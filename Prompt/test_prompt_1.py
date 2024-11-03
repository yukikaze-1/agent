# Project:      Agent Test Script
# Author:       yomu
# Time:         2024/10/29
# Version:      0.1
# Description:  Test script for agent main

import unittest
from unittest.mock import patch
import json
from prompt_1 import KeywordTaskHandler, PromptOptimizationHandler, GeneralTaskHandler

class TestAgentHandlers(unittest.TestCase):
    @patch('prompt_1.call_llm')
    def test_keyword_task_handler(self, mock_call_llm):
        # Mock response from the LLM
        mock_call_llm.return_value = json.dumps({
            "target": "extract keywords",
            "keywords": ["test", "keyword"]
        })

        handler = KeywordTaskHandler()
        content = "This is a test content for keyword extraction."
        keywords = handler.summarize_keywords(content)

        self.assertEqual(keywords, ["test", "keyword"], "The extracted keywords do not match the expected output.")

    @patch('prompt_1.call_llm')
    def test_prompt_optimization_handler(self, mock_call_llm):
        # Mock response from the LLM
        mock_call_llm.return_value = json.dumps({
            "target": "optimize prompt",
            "process": {
                "step1": "Analyze the goal",
                "step2": "Break down into tasks",
                "step3": "Organize tasks"
            }
        })

        handler = PromptOptimizationHandler()
        content = "I need to achieve a complex goal."
        constraints = "No legal advice."
        prompt = handler.generate_prompt(content=content, constraints=constraints)
        response = handler.call_model(prompt)

        self.assertIn("step1", response, "The response does not contain the expected step1 key.")

    @patch('prompt_1.call_llm')
    def test_general_task_handler(self, mock_call_llm):
        # Mock response from the LLM
        mock_call_llm.return_value = json.dumps({
            "action": {
                "name": "perform_action",
                "args": {
                    "args_name": "argument_value"
                }
            },
            "thoughts": {
                "text": "Performing the action",
                "plan": "Step-by-step plan",
                "criticism": "No issues",
                "step": "First step",
                "reasoning": "Logical reasoning"
            }
        })

        handler = GeneralTaskHandler()
        query = "How do I improve my productivity?"
        constraints = "No illegal methods."
        memory = "Previous discussions."
        resources = "Available tools."
        prompt = handler.generate_prompt(query=query, constraints=constraints, memory=memory, resources=resources)
        response = handler.call_model(prompt)

        self.assertIn("action", response, "The response does not contain the expected action key.")

if __name__ == '__main__':
    unittest.main()
