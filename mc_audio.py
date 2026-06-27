"""
Procedural soundtrack + SFX generator for Minecraft TABS.
Generates rich, non-chiptune audio (layered pads, bass, melody, soft drums,
reverb) and short battle SFX as WAV files. Files are cached in assets/ so they
are only synthesized once.
"""
import os
import wave
import struct
import numpy as np

SR = 44100


# ----------------------------------------------------------------------------
# Low level synthesis helpers
# ----------------------------------------------------------------------------
def _t(dur):
    return np.linspace(0, dur, int(SR * dur), endpoint=False)


def midi_freq(n):
    return 440.0 * 2 ** ((n - 69) / 12.0)


def adsr(n, a=0.01, d=0.1, s=0.7, r=0.2):
    """Attack/decay/sustain/release envelope for n samples."""
    a_n = max(1, int(a * SR))
    d_n = max(1, int(d * SR))
    r_n = max(1, int(r * SR))
    s_n = max(1, n - a_n - d_n - r_n)
    env = np.concatenate([
        np.linspace(0, 1, a_n),
        np.linspace(1, s, d_n),
        np.full(s_n, s),
        np.linspace(s, 0, r_n),
    ])
    if len(env) < n:
        env = np.concatenate([env, np.zeros(n - len(env))])
    return env[:n]


def soft_osc(freq, dur, detune=0.004, partials=(1.0, 0.5, 0.25), vibrato=0.0):
    """Warm tone: a few sine partials, slight detune, optional vibrato."""
    t = _t(dur)
    sig = np.zeros_like(t)
    vib = np.sin(2 * np.pi * 5.5 * t) * vibrato if vibrato else 0.0
    for i, amp in enumerate(partials, start=1):
        f = freq * i
        sig += amp * np.sin(2 * np.pi * f * (t) + vib)
        sig += amp * 0.5 * np.sin(2 * np.pi * f * (1 + detune) * t)
    sig /= np.max(np.abs(sig)) + 1e-9
    return sig


def tri_osc(freq, dur, vibrato=0.0):
    t = _t(dur)
    vib = np.sin(2 * np.pi * 6 * t) * vibrato if vibrato else 0.0
    ph = (freq * t + vib) % 1.0
    return 2 * np.abs(2 * ph - 1) - 1


def reverb(sig, decay=0.35, n_taps=5, spread=0.045):
    """Cheap multi-tap feedback reverb to remove the 'bleepy' chiptune feel."""
    out = sig.copy()
    for k in range(1, n_taps + 1):
        delay = int(spread * k * SR)
        if delay >= len(sig):
            break
        echo = np.zeros_like(sig)
        echo[delay:] = sig[:-delay] * (decay ** k)
        out += echo
    return out


def _place(buf, sig, start):
    end = min(len(buf), start + len(sig))
    if end > start:
        buf[start:end] += sig[:end - start]


def write_wav(path, left, right=None):
    if right is None:
        right = left
    m = max(np.max(np.abs(left)), np.max(np.abs(right)), 1e-9)
    left = (left / m) * 0.92
    right = (right / m) * 0.92
    inter = np.empty(left.size + right.size, dtype=np.float32)
    inter[0::2] = left
    inter[1::2] = right
    data = (np.clip(inter, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, 'w') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


# ----------------------------------------------------------------------------
# Music
# ----------------------------------------------------------------------------
def _build_track(chords, melody, bpm, bars, drums=True, lead_gain=0.5):
    beat = 60.0 / bpm
    bar = beat * 4
    total = bar * bars
    n = int(total * SR)
    left = np.zeros(n)
    right = np.zeros(n)

    # chord pad — one chord per bar
    for b in range(bars):
        ch = chords[b % len(chords)]
        start = int(b * bar * SR)
        for j, note in enumerate(ch):
            f = midi_freq(note)
            tone = soft_osc(f, bar, partials=(1.0, 0.45, 0.22, 0.12))
            env = adsr(len(tone), a=0.25, d=0.4, s=0.7, r=0.5)
            tone *= env * 0.20
            pan = 0.5 + (j - len(ch) / 2) * 0.12
            _place(left, tone * (1 - pan * 0.5), start)
            _place(right, tone * (0.5 + pan * 0.5), start)

    # bass — root note, two hits per bar
    for b in range(bars):
        root = chords[b % len(chords)][0] - 12
        for sub in (0, 2):
            start = int((b * bar + sub * beat) * SR)
            f = midi_freq(root)
            tone = (np.sin(2 * np.pi * f * _t(beat * 1.8)) * 0.6
                    + tri_osc(f, beat * 1.8) * 0.4)
            tone *= adsr(len(tone), a=0.005, d=0.15, s=0.6, r=0.3) * 0.33
            _place(left, tone, start)
            _place(right, tone, start)

    # lead melody — triangle with vibrato, gentle
    pos = 0.0
    for (note, dur) in melody:
        start = int(pos * beat * SR)
        if note is not None:
            f = midi_freq(note)
            tone = tri_osc(f, dur * beat, vibrato=0.012)
            tone += soft_osc(f, dur * beat, partials=(1.0, 0.3)) * 0.4
            tone *= adsr(len(tone), a=0.02, d=0.1, s=0.6, r=0.25) * lead_gain
            _place(left, tone * 0.85, start)
            _place(right, tone, start)
        pos += dur
        if pos * beat >= total:
            break

    # soft percussion for drive (filtered, not bleepy)
    if drums:
        for b in range(bars):
            for beat_i in range(4):
                start = int((b * bar + beat_i * beat) * SR)
                if beat_i in (0, 2):  # kick
                    kt = _t(0.18)
                    f = 110 * np.exp(-kt * 28)
                    kick = np.sin(2 * np.pi * f * kt) * np.exp(-kt * 16) * 0.5
                    _place(left, kick, start)
                    _place(right, kick, start)
                # hat
                ht = _t(0.05)
                hat = (np.random.randn(len(ht)) * np.exp(-ht * 60) * 0.06)
                _place(left, hat, start)
                _place(right, hat, start)

    left = reverb(left, decay=0.3)
    right = reverb(right, decay=0.3)
    return left, right


def generate_battle_theme(path):
    # i - VI - VII - i  in A minor-ish, epic
    Am = [57, 60, 64]
    F = [53, 57, 60]
    G = [55, 59, 62]
    Em = [52, 55, 59]
    C = [48, 52, 55]
    chords = [Am, F, C, G, Am, F, G, Em]
    # melody (note, duration in beats); minor pentatonic flavour
    mel = [
        (69, 1), (72, 1), (71, 0.5), (69, 0.5), (67, 1),
        (65, 1), (69, 1), (67, 0.5), (65, 0.5), (64, 1),
        (72, 1), (74, 1), (72, 0.5), (71, 0.5), (69, 1),
        (67, 1), (69, 2), (None, 1),
        (69, 1), (72, 1), (76, 1), (74, 0.5), (72, 0.5),
        (71, 1), (69, 1), (67, 1), (69, 1),
        (74, 1), (72, 1), (71, 0.5), (69, 0.5), (67, 2),
        (64, 2), (None, 2),
    ]
    l, r = _build_track(chords, mel, bpm=128, bars=8, drums=True, lead_gain=0.42)
    write_wav(path, l, r)


def generate_menu_theme(path):
    Am = [57, 60, 64]
    F = [53, 57, 60]
    C = [48, 52, 55]
    G = [55, 59, 62]
    chords = [C, G, Am, F]
    mel = [
        (72, 2), (76, 2), (74, 1), (72, 1), (71, 2),
        (69, 2), (72, 2), (67, 2), (69, 4),
        (None, 2), (76, 2), (74, 2), (72, 2),
    ]
    l, r = _build_track(chords, mel, bpm=92, bars=4, drums=False, lead_gain=0.5)
    write_wav(path, l, r)


# ----------------------------------------------------------------------------
# SFX
# ----------------------------------------------------------------------------
def sfx_hit(path):
    t = _t(0.12)
    sig = (np.sin(2 * np.pi * 180 * t) * np.exp(-t * 30)
           + np.random.randn(len(t)) * np.exp(-t * 45) * 0.4)
    write_wav(path, sig)


def sfx_death(path):
    t = _t(0.4)
    f = 300 * np.exp(-t * 4)
    sig = np.sin(2 * np.pi * f * t) * np.exp(-t * 5) * 0.7
    write_wav(path, reverb(sig, 0.25))


def sfx_explode(path):
    t = _t(0.7)
    noise = np.random.randn(len(t)) * np.exp(-t * 6)
    rumble = np.sin(2 * np.pi * 60 * t) * np.exp(-t * 4)
    sig = (noise * 0.7 + rumble * 0.6)
    write_wav(path, reverb(sig, 0.3))


def sfx_bow(path):
    t = _t(0.25)
    f = np.linspace(900, 300, len(t))
    sig = np.sin(2 * np.pi * f * t) * np.exp(-t * 10) * 0.5
    write_wav(path, sig)


def sfx_sonic(path):
    t = _t(0.6)
    f = np.linspace(160, 40, len(t))
    sig = (np.sin(2 * np.pi * f * t)
           + 0.5 * np.sin(2 * np.pi * f * 2 * t)) * np.exp(-t * 3) * 0.8
    write_wav(path, reverb(sig, 0.4))


def sfx_win(path):
    seq = [60, 64, 67, 72]
    parts = []
    for i, m in enumerate(seq):
        tone = soft_osc(midi_freq(m), 0.22, partials=(1, 0.5, 0.3))
        tone *= adsr(len(tone), a=0.01, d=0.05, s=0.7, r=0.1) * 0.6
        parts.append(tone)
    sig = np.concatenate(parts)
    write_wav(path, reverb(sig, 0.35))


def sfx_place(path):
    t = _t(0.1)
    sig = np.sin(2 * np.pi * 520 * t) * np.exp(-t * 25) * 0.5
    write_wav(path, sig)


def sfx_start(path):
    t = _t(0.5)
    f = np.linspace(220, 660, len(t))
    sig = (np.sin(2 * np.pi * f * t) * np.exp(-t * 3)) * 0.6
    write_wav(path, reverb(sig, 0.3))


SFX = {
    'hit': sfx_hit,
    'death': sfx_death,
    'explode': sfx_explode,
    'bow': sfx_bow,
    'sonic': sfx_sonic,
    'win': sfx_win,
    'place': sfx_place,
    'start': sfx_start,
}


def generate_all(assets_dir):
    """Generate every audio file if missing. Returns dict of name -> path."""
    os.makedirs(assets_dir, exist_ok=True)
    paths = {}

    music = {
        'battle': ('battle_theme.wav', generate_battle_theme),
        'menu': ('menu_theme.wav', generate_menu_theme),
    }
    for name, (fn, fn_gen) in music.items():
        p = os.path.join(assets_dir, fn)
        if not os.path.exists(p):
            fn_gen(p)
        paths[name] = p

    for name, fn_gen in SFX.items():
        p = os.path.join(assets_dir, f'sfx_{name}.wav')
        if not os.path.exists(p):
            fn_gen(p)
        paths[name] = p

    return paths


if __name__ == '__main__':
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
    print('Generating audio in', here)
    out = generate_all(here)
    for k, v in out.items():
        print(' ', k, '->', os.path.basename(v))
    print('done')
