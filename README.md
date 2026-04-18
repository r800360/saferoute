# SafeRoute: Agentic Hazard-Aware Urban Navigation in CARLA

Multi-agent autonomous driving copilot in CARLA using an agentic workflow (LangGraph-style reasoning).

## Overview
SafeRoute decomposes navigation into:
- Perception Agent
- Planning Agent
- Safety/Critic Agent
- Execution Agent

Agents iteratively reason over scenes, propose actions, and refine decisions under uncertainty.

## Features
- Modular agent-based architecture
- Hazard-aware decision-making
- Interpretable decision traces
- Evaluation in CARLA under varied traffic and weather

## Setup
1. Install CARLA 0.9.15 and verify the simulator launches. The official CARLA quickstart supports Python-based scripting, and CARLA 0.9.15 is a stable packaged release.
2. Create a Python environment that matches your CARLA Python API package.
3. Install dependencies:
```bash
pip install -r requirements.txt
```
4. Start the CARLA server before running SafeRoute.

## Notes
- Use a CARLA Python API version that matches your simulator version.
- Native Windows or Linux is generally preferable to WSL for simulator stability.
