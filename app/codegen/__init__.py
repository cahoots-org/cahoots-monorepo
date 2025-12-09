"""
Code Generation Module

This module contains the AI-powered code generation system that transforms
event models (slices) into working, tested code using a test-first approach.

Components:
- agents: LLM-powered workers with tool access (Scaffold, Test, Code, Fix, etc.)
- orchestrator: Coordinates the generation process and manages state
- stacks: Tech stack configurations (Node.js, Python, etc.)
"""
