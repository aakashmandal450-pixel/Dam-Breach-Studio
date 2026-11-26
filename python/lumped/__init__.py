"""Dam Breach Studio — 1-D lumped morphodynamic breach model.

One reservoir storage and one evolving breach section (trapezoid on the dam crest and downstream
slope), advanced as an ODE system in time. No spatial grid.

Design:   claude/LUMPED_1D_PLAN_2026-11-20.md (project notes)
Roadmap:  claude/ROADMAP_LUMPED_1D_2026-11-20.md
Review:   claude/ENGINE_1D_PHYSICS_REVIEW_2026-11-20.md

Physics laws are imported from breach_engine_2d_v3_2.py where possible, so both engines use
identical formulas. Every coefficient is sourced or is one of the calibration factors f_kd, C_h, f_t.
"""

__version__ = "0.2.0"
