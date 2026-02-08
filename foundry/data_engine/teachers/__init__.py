# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Teacher models — API and local model abstraction for data synthesis."""

from foundry.data_engine.teachers.base import Message, Teacher, TeacherResponse
from foundry.data_engine.teachers.api_teacher import APITeacher
from foundry.data_engine.teachers.local_teacher import LocalTeacher

__all__ = ["Teacher", "TeacherResponse", "Message", "APITeacher", "LocalTeacher"]
