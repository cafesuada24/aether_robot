# Autonomous Mobile Robot with LLM & MCP Integration

## Overview

This repository contains an end-to-end **Autonomous Mobile Robot (AMR)** system integrated with a **Large Language Model (LLM)** via the **Model Context Protocol (MCP)** to enable **natural language command and interaction**.

The project demonstrates how modern AI systems can be cleanly integrated with robotics software to bridge human intent and robotic execution. Natural language instructions are interpreted by an LLM, translated into structured actions, and executed by a ROS-based mobile robot stack with full feedback loops.

This repository is designed as:
- A **reference architecture** for LLM-driven robotics
- A **research and engineering showcase** for AI + robotics integration
- A **practical foundation** for extending autonomous navigation, planning, and human–robot interaction

---

## Key Capabilities

- Natural language command execution (e.g., *“Go to the charging station and wait”*)
- LLM-driven reasoning and intent decomposition
- MCP-based tool and context orchestration
- Autonomous navigation using ROS 2 / Nav2
- Waypoint management and semantic location queries
- Bidirectional feedback from robot to LLM
- Modular, clean-architecture-inspired design

---

## Core Concepts

### 1. Natural Language Control
Users interact with the robot using plain language. The LLM interprets intent, resolves ambiguity, and decides which robot capabilities to invoke.

### 2. Model Context Protocol (MCP)
MCP provides a structured interface between the LLM and robotic services:
- Tools are exposed as callable actions
- Context (robot state, maps, waypoints) is dynamically injected
- Execution results are fed back to the LLM

### 3. Clean Architecture Principles
The system separates:
- **Domain logic** (navigation concepts, waypoints)
- **Application logic** (use cases, orchestration)
- **Infrastructure** (ROS, sensors, actuators, MCP server)

This ensures extensibility, testability, and long-term maintainability.

---


## Supported Commands (Examples)

- “Where am I?”
- “Go to the kitchen.”
- “Save my current position as `dock`.”
- “List all waypoints.”
- “Navigate to the nearest charging station.”
- “Cancel the current navigation task.”

---

## Simulation and Digital Twin

The project includes a **digital twin simulator** to allow:
- Rapid development without physical hardware
- Safe testing of navigation and reasoning
- Deterministic debugging of LLM behavior

Simulation mirrors real robot interfaces to ensure minimal divergence from deployment.

---

## Demo Video

This section showcases the system in action, highlighting natural language interaction, LLM reasoning, and autonomous robot execution.

### System Demonstration

[![Demonstration of Robot's Mapping functionality](https://img.youtube.com/vi/DAsgki0NNdw/0.jpg)](https://youtu.be/DAsgki0NNdw)

---

## Technology Stack

**Robotics**
- ROS 2
- Nav2
- SLAM / AMCL
- TF2

**AI & Orchestration**
- Large Language Models (provider-agnostic)
- Model Context Protocol (MCP)

**Languages**
- Python (LLM, MCP, orchestration)
- C++ (performance-critical ROS components)

**Infrastructure**
- Docker
- DDS middleware
- Optional cloud-based LLM deployment

---

## Design Goals

- Clear separation between AI reasoning and robot execution
- Deterministic, auditable robot actions
- LLM as a planner and interpreter, not a controller
- Minimal coupling between AI and robotics layers
- Production-grade structure, not a demo script

---

## Intended Audience

- Robotics engineers exploring LLM integration
- AI engineers working on embodied intelligence
- Researchers in human–robot interaction
- Teams building next-generation autonomous systems

---

## Disclaimer

This project is intended for research and engineering experimentation. While safety considerations are incorporated, real-world deployment requires additional validation, certification, and fail-safe mechanisms.

---

## License

Proprietary

---

## Contact

For questions, discussions, or collaboration, please open an issue or reach out through the repository’s discussion board.
