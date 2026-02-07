# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Teacher models — API and local model abstraction for data synthesis."""

from foundry.data_engine.teachers.base import Message, Teacher, TeacherResponse
from foundry.data_engine.teachers.api_teacher import APITeacher
from foundry.data_engine.teachers.local_teacher import LocalTeacher

__all__ = ["Teacher", "TeacherResponse", "Message", "APITeacher", "LocalTeacher"]
