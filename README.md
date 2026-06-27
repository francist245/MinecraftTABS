# Minecraft TABS ⚔️🟩

**Totally Accurate Battle Simulator — Minecraft edition!** A real **3D** voxel
battle sim where you place two blocky armies of Minecraft mobs and watch them
fight to the last block. Built with [Ursina](https://www.ursinaengine.org/)
(Panda3D) and a fully procedural, **non‑chiptune** soundtrack synthesized with
NumPy.

By Toby.

![3D](https://img.shields.io/badge/3D-Ursina-brightgreen) ![mobs](https://img.shields.io/badge/mobs-16-blue)

## ✨ Features
- **Real 3D** — orbit/zoom/pan camera over a voxel battlefield.
- **16 blocky mobs** with unique 3D models, stats and special abilities.
- **The newest mobs**: Warden, Breeze, Camel, Sniffer, Allay, Armadillo,
  Creaking and Bogged — plus classics (Zombie, Skeleton, Creeper, Iron Golem,
  Piglin Brute, Wolf, Pillager).
- **Structures**: Trial Chamber ruins, an Ancient City pillar, a village house
  and oak trees frame the arena.
- **TABS‑style gameplay**: gold budget, place units on your half, press start,
  physics‑y knockback, ragdoll deaths, projectiles and AoE.
- **Epic procedural soundtrack** (layered pads, bass, melody, soft drums &
  reverb) + battle SFX — generated once and cached in `assets/`.

## 🐾 Special abilities
| Mob | Type | Special |
| --- | --- | --- |
| Warden 🩵 | Boss / ranged | Sonic boom, monstrous HP |
| Breeze 💨 | Ranged | Wind charges with huge knockback |
| Camel 🐫 | Tank | Dash with knockback |
| Sniffer 🟥 | Tank | Enormous HP wall |
| Allay 🔵 | Support | Flies and **heals** allies |
| Armadillo 🟤 | Bruiser | Rolls in, 45% armour |
| Creaking 🟧 | Bruiser | **Revives once** |
| Bogged 🟢 | Ranged | Poison arrows (damage over time) |
| Creeper 💚 | Suicide | Rushes in and **explodes** |
| Iron Golem ⬜ | Tank | Massive knockback |
| ...and more | | |

## 🎮 Controls
| Input | Action |
| --- | --- |
| **Left click** | Place selected unit on YOUR half |
| **1–8 / Q W E A T Y** or buttons | Pick a unit |
| **TAB** | Switch placing team (Red / Blue) |
| **SPACE** | START the battle |
| **R** | Reset to setup |
| **C** | Clear your placed units |
| **Right‑drag** | Orbit camera · **scroll** zoom · **middle‑drag** pan |

Red places on the near half, Blue on the far half. Each side starts with
**1400 gold**.

## ▶️ Run
```bash
pip install ursina numpy
python tabs_mc.py
```
Audio is synthesized on first launch (<1s) and cached in `assets/`.

## 🗂️ Files
- `tabs_mc.py` — the game (world, mobs, combat AI, UI).
- `mc_audio.py` — procedural music + SFX generator.
- `assets/` — generated `.wav` soundtrack and sound effects.

Launchable from Toby's Ops Centre game launcher. 🎛️
