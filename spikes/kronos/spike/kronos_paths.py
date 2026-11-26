"""Kronos sampler that returns every sample path (the vendor code averages them).

Differences from vendor `auto_regressive_inference` (vendor-Kronos/model/kronos.py:389):
- returns all N paths, not their mean;
- the model and tokenizer are put in eval() mode (the vendor predictor leaves dropout on);
- sampling is Gumbel-max with noise from one seeded CPU generator per Forecast, so a
  Forecast's paths do not depend on what else is in the batch (needed for the
  truncation test in docs/research/kronos-edge-test.md);
- future bar timestamps are supplied by the caller from a trading-hours rule, never
  from the real data.
Normalisation is the vendor's: per-window mean/std over the lookback only, clip ±5.
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

from spike.calendar import future_bar_times  # noqa: F401  (re-exported)

VENDOR = Path(__file__).resolve().parents[1] / "vendor-Kronos"
sys.path.insert(0, str(VENDOR))
from model import Kronos, KronosTokenizer  # noqa: E402
from model.kronos import top_k_top_p_filtering  # noqa: E402

PRICE_COLS = ["open", "high", "low", "close"]
CLIP = 5.0

MODELS = {
    "mini": ("NeoQuasar/Kronos-mini", "NeoQuasar/Kronos-Tokenizer-2k", 2048),
    "small": ("NeoQuasar/Kronos-small", "NeoQuasar/Kronos-Tokenizer-base", 512),
    "base": ("NeoQuasar/Kronos-base", "NeoQuasar/Kronos-Tokenizer-base", 512),
}


@dataclass(frozen=True)
class SamplerConfig:
    model: str = "small"
    n_paths: int = 30
    horizon: int = 24
    lookback: int = 400
    temperature: float = 1.0
    top_p: float = 0.9
    top_k: int = 0
    seed: int = 20261126


# Pinned Hugging Face revisions (docs/research/kronos-edge-test.md, Reproducibility).
REVISIONS = {
    "NeoQuasar/Kronos-small": "901c26c1332695a2a8f243eb2f37243a37bea320",
    "NeoQuasar/Kronos-Tokenizer-base": "0e0117387f39004a9016484a186a908917e22426",
}


def load(model_size: str, device: str):
    name, tok_name, max_ctx = MODELS[model_size]
    tok = KronosTokenizer.from_pretrained(tok_name, revision=REVISIONS.get(tok_name)).to(device).eval()
    mdl = Kronos.from_pretrained(name, revision=REVISIONS.get(name)).to(device).eval()
    return tok, mdl, max_ctx


def forecast_seed(base_seed: int, key: str) -> int:
    """Stable 63-bit seed for one Forecast, e.g. key = 'EURUSD|2025-07-01T13:00Z'."""
    h = hashlib.sha256(f"{base_seed}|{key}".encode()).digest()
    return int.from_bytes(h[:8], "little") & ((1 << 63) - 1)


def time_features(ts: pd.DatetimeIndex) -> np.ndarray:
    return np.stack([ts.minute, ts.hour, ts.weekday, ts.day, ts.month], axis=1).astype(np.float32)


def _gumbel_sample(logits, gens, n_paths, cfg: SamplerConfig):
    """logits: (items*n_paths, V). One generator per item supplies that item's noise."""
    logits = logits / cfg.temperature
    if cfg.top_k > 0 or cfg.top_p < 1.0:
        logits = top_k_top_p_filtering(logits, top_k=cfg.top_k, top_p=cfg.top_p)
    v = logits.size(-1)
    u = torch.cat([torch.rand(n_paths, v, generator=g) for g in gens])
    u = u.clamp_(1e-10, 1 - 1e-10).to(logits.device)
    g = -torch.log(-torch.log(u))
    return torch.argmax(F.log_softmax(logits, dim=-1) + g, dim=-1, keepdim=True)


@torch.no_grad()
def sample_paths(tok, mdl, max_ctx, windows, x_times, y_times, keys, cfg: SamplerConfig):
    """Sample N paths for each Forecast in the batch.

    windows: list of (lookback, 4) float arrays of OHLC (mid), oldest first.
    x_times: list of DatetimeIndex (lookback,) bar-open UTC times of the window.
    y_times: list of DatetimeIndex (horizon,) generated future bar-open UTC times.
    keys:    list of str, one per Forecast, for the seed.
    Returns float32 array (items, n_paths, horizon, 4) of OHLC prices.
    """
    device = next(mdl.parameters()).device
    n, h = cfg.n_paths, cfg.horizon
    xs, means, stds = [], [], []
    for w in windows:
        x = np.concatenate([w, np.zeros((len(w), 2), np.float32)], axis=1).astype(np.float32)  # volume, amount = 0
        m, s = x.mean(0), x.std(0)
        xs.append(np.clip((x - m) / (s + 1e-5), -CLIP, CLIP))
        means.append(m)
        stds.append(s)
    x = torch.from_numpy(np.stack(xs)).to(device)
    xs_t = torch.from_numpy(np.stack([time_features(t) for t in x_times])).to(device)
    ys_t = torch.from_numpy(np.stack([time_features(t) for t in y_times])).to(device)

    rep = lambda t: t.unsqueeze(1).repeat(1, n, *([1] * (t.dim() - 1))).reshape(-1, *t.shape[1:])
    x, xs_t, ys_t = rep(x), rep(xs_t), rep(ys_t)
    gens = [torch.Generator().manual_seed(forecast_seed(cfg.seed, k)) for k in keys]

    pre, post = tok.encode(x, half=True)
    seq_len = x.size(1)
    full_stamp = torch.cat([xs_t, ys_t], dim=1)
    for i in range(h):
        cur = seq_len + i
        start = max(0, cur - max_ctx)
        s1_logits, ctx = mdl.decode_s1(pre[:, start:cur], post[:, start:cur], full_stamp[:, start:cur].contiguous())
        s1 = _gumbel_sample(s1_logits[:, -1, :], gens, n, cfg)
        s2_logits = mdl.decode_s2(ctx, s1)
        s2 = _gumbel_sample(s2_logits[:, -1, :], gens, n, cfg)
        pre = torch.cat([pre, s1], dim=1)
        post = torch.cat([post, s2], dim=1)

    total = seq_len + h
    start = max(0, total - max_ctx)
    z = tok.decode([pre[:, start:total].contiguous(), post[:, start:total].contiguous()], half=True)
    z = z[:, -h:, :4].reshape(len(windows), n, h, 4).cpu().numpy()
    m = np.stack(means)[:, None, None, :4]
    s = np.stack(stds)[:, None, None, :4]
    return (z * (s + 1e-5) + m).astype(np.float32)


# ---------------------------------------------------------------------------
# Fast path: KV cache with the context shared across the N paths of a Forecast.
# Same model, same Gumbel noise and same sampling as sample_paths (the reference); only
# the arithmetic is reorganised. Exact only while lookback + horizon <= max_context (no
# sliding window), which the Edge test's 400 + 24 satisfies; checked below.
# ---------------------------------------------------------------------------


def _rope(x, cos, sin):
    x1, x2 = x.chunk(2, dim=-1)
    return x * cos + torch.cat((-x2, x1), dim=-1) * sin


def _heads(t, nh):
    b, l, d = t.shape
    return t.view(b, l, nh, d // nh).transpose(1, 2)


def _shared_attention(q, kp, vp, ks, vs, n):
    """q: (B*n, h, 1, hd); kp, vp: (B, h, L0, hd) shared prefix; ks, vs: (B*n, h, S, hd) or None."""
    bn, h, _, hd = q.shape
    b = bn // n
    q5 = q.view(b, n, h, 1, hd)
    scale = hd ** -0.5
    sp = torch.einsum("bnhqd,bhkd->bnhqk", q5, kp) * scale
    if ks is not None:
        ss = torch.einsum("bnhqd,bnhkd->bnhqk", q5, ks.view(b, n, h, -1, hd)) * scale
        s = torch.cat([sp, ss], dim=-1)
    else:
        s = sp
    a = torch.softmax(s, dim=-1)
    l0 = kp.shape[2]
    out = torch.einsum("bnhqk,bhkd->bnhqd", a[..., :l0], vp)
    if ks is not None:
        out = out + torch.einsum("bnhqk,bnhkd->bnhqd", a[..., l0:], vs.view(b, n, h, -1, hd))
    return out.reshape(bn, h, 1, hd)


@torch.no_grad()
def sample_paths_fast(tok, mdl, max_ctx, windows, x_times, y_times, keys, cfg: SamplerConfig):
    """Same contract as sample_paths."""
    device = next(mdl.parameters()).device
    n, h = cfg.n_paths, cfg.horizon
    assert cfg.lookback + h <= max_ctx, "the fast path is exact only without a sliding window"
    xs, means, stds = [], [], []
    for w in windows:
        x = np.concatenate([w, np.zeros((len(w), 2), np.float32)], axis=1).astype(np.float32)
        m, s = x.mean(0), x.std(0)
        xs.append(np.clip((x - m) / (s + 1e-5), -CLIP, CLIP))
        means.append(m)
        stds.append(s)
    b = len(windows)
    x = torch.from_numpy(np.stack(xs)).to(device)
    xs_t = torch.from_numpy(np.stack([time_features(t) for t in x_times])).to(device)
    ys_t = torch.from_numpy(np.stack([time_features(t) for t in y_times])).to(device)
    gens = [torch.Generator().manual_seed(forecast_seed(cfg.seed, k)) for k in keys]

    pre, post = tok.encode(x, half=True)  # (B, L0) each; identical across paths, so encode once
    l0 = pre.shape[1]
    nh = mdl.n_heads
    hd = mdl.d_model // nh
    inv = mdl.transformer[0].self_attn.rotary.inv_freq
    t_ = torch.arange(l0 + h, device=device).type_as(inv)
    emb = torch.cat([torch.einsum("i,j->ij", t_, inv)] * 2, dim=-1)
    cos_all, sin_all = emb.cos()[None, None], emb.sin()[None, None]

    # Prefill the shared context once per Forecast (causal, exactly as the vendor forward).
    hx = mdl.embedding([pre, post]) + mdl.time_emb(xs_t)
    kps, vps = [], []
    cos, sin = cos_all[:, :, :l0], sin_all[:, :, :l0]
    for blk in mdl.transformer:
        a = blk.self_attn
        z = blk.norm1(hx)
        q, k, v = _heads(a.q_proj(z), nh), _heads(a.k_proj(z), nh), _heads(a.v_proj(z), nh)
        q, k = _rope(q, cos, sin), _rope(k, cos, sin)
        kps.append(k)
        vps.append(v)
        o = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        hx = hx + a.out_proj(o.transpose(1, 2).reshape(b, l0, -1))
        hx = hx + blk.ffn(blk.norm2(hx))
    ctx = mdl.norm(hx)  # (B, L0, d): the "context" decode_s2 attends over
    ca = mdl.dep_layer.cross_attn  # its RoPE runs at position 0 (identity), so no rotation here
    ckp, cvp = _heads(ca.k_proj(ctx), ca.n_heads), _heads(ca.v_proj(ctx), ca.n_heads)

    def s2_logits(last_ctx, s1, cks, cvs):
        sib = mdl.embedding.emb_s1(s1)  # (B*n, 1, d)
        qq = _heads(ca.q_proj(sib), ca.n_heads)
        o = _shared_attention(qq, ckp, cvp, cks, cvs, n)
        att = ca.out_proj(o.transpose(1, 2).reshape(b * n, 1, -1))
        return mdl.head.cond_forward(mdl.dep_layer.norm(last_ctx + att))[:, -1, :]

    last = ctx[:, -1:, :].repeat_interleave(n, dim=0)  # (B*n, 1, d)
    s1 = _gumbel_sample(mdl.head(last)[:, -1, :], gens, n, cfg)
    s2 = _gumbel_sample(s2_logits(last, s1, None, None), gens, n, cfg)
    gen_pre, gen_post = [s1], [s2]
    kss = [None] * len(mdl.transformer)
    vss = [None] * len(mdl.transformer)
    cks = cvs = None
    for i in range(1, h):
        p = l0 + i - 1  # position of the token just sampled
        hx = mdl.embedding([s1, s2]) + mdl.time_emb(full_stamp_step(xs_t, ys_t, i - 1, n))
        cos, sin = cos_all[:, :, p:p + 1], sin_all[:, :, p:p + 1]
        for j, blk in enumerate(mdl.transformer):
            a = blk.self_attn
            z = blk.norm1(hx)
            q, k, v = _heads(a.q_proj(z), nh), _heads(a.k_proj(z), nh), _heads(a.v_proj(z), nh)
            q, k = _rope(q, cos, sin), _rope(k, cos, sin)
            kss[j] = k if kss[j] is None else torch.cat([kss[j], k], dim=2)
            vss[j] = v if vss[j] is None else torch.cat([vss[j], v], dim=2)
            o = _shared_attention(q, kps[j], vps[j], kss[j], vss[j], n)
            hx = hx + a.out_proj(o.transpose(1, 2).reshape(b * n, 1, -1))
            hx = hx + blk.ffn(blk.norm2(hx))
        last = mdl.norm(hx)
        ck, cv = _heads(ca.k_proj(last), ca.n_heads), _heads(ca.v_proj(last), ca.n_heads)
        cks = ck if cks is None else torch.cat([cks, ck], dim=2)
        cvs = cv if cvs is None else torch.cat([cvs, cv], dim=2)
        s1 = _gumbel_sample(mdl.head(last)[:, -1, :], gens, n, cfg)
        s2 = _gumbel_sample(s2_logits(last, s1, cks, cvs), gens, n, cfg)
        gen_pre.append(s1)
        gen_post.append(s2)

    full_pre = torch.cat([pre.repeat_interleave(n, dim=0)] + gen_pre, dim=1)
    full_post = torch.cat([post.repeat_interleave(n, dim=0)] + gen_post, dim=1)
    z = tok.decode([full_pre, full_post], half=True)
    z = z[:, -h:, :4].reshape(b, n, h, 4).cpu().numpy()
    m = np.stack(means)[:, None, None, :4]
    s = np.stack(stds)[:, None, None, :4]
    return (z * (s + 1e-5) + m).astype(np.float32)


def full_stamp_step(xs_t, ys_t, j, n):
    """Time features of future bar j (0-based), repeated for the n paths: (B*n, 1, 5)."""
    return ys_t[:, j:j + 1, :].repeat_interleave(n, dim=0)
