# Requirements Document

## Introduction

Fix identity confusion bug: AI responds as Alex instead of as journaling assistant.

## Requirements

### R1 - Don't impersonate the user
The assistant SHALL never speak as Alex. It SHALL always address Alex as "you/your".

### R2 - Use memories as data, not persona  
Memories may be referenced in second person. If no relevant memory exists, respond normally.

### R3 - Journaling behavior
Each reply: 1–2 lines of reflection + exactly 1 incisive follow-up question.