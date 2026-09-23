import re
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.database.models.models import TestCase, TestStep, Environment, EnvironmentType

class ActionSafetyLevel:
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    DESTRUCTIVE = "DESTRUCTIVE"
    BLOCKED = "BLOCKED"

class SafetyValidationResult:
    def __init__(self, is_valid: bool, safety_level: str, error_message: Optional[str] = None):
        self.is_valid = is_valid
        self.safety_level = safety_level
        self.error_message = error_message

class SafetyValidator:
    """
    Validates test cases, steps, and environments against safety policies:
    - Blocks destructive actions (delete, drop, wipe, cancel account)
    - Blocks payments / credential theft
    - Guards against executing against production environments
    - Verifies required steps, targets, and expected outcomes exist
    """

    SUPPORTED_ACTIONS = {"navigate", "click", "fill", "select", "assert", "submit", "press", "check"}

    DESTRUCTIVE_KEYWORDS = [
        "delete", "remove", "drop", "destroy", "cancel_account",
        "purge", "wipe", "terminate", "truncate"
    ]

    BLOCKED_KEYWORDS = [
        "payment", "stripe", "paypal", "credit_card", "checkout_live",
        "real_charge", "transfer_money", "ssn", "steal", "hack"
    ]

    @classmethod
    def classify_step(cls, step: TestStep) -> Tuple[str, Optional[str]]:
        action = step.action.lower().strip()
        target = (step.target or "").lower()
        val = (step.value or "").lower()
        expected = (step.expected_result or "").lower()

        text_to_check = f"{action} {target} {val} {expected}"

        # 1. Check for blocked keywords
        for keyword in cls.BLOCKED_KEYWORDS:
            if keyword in text_to_check:
                return ActionSafetyLevel.BLOCKED, f"Blocked high-risk action containing prohibited keyword: '{keyword}'"

        # 2. Check for destructive operations
        for keyword in cls.DESTRUCTIVE_KEYWORDS:
            if keyword in text_to_check:
                return ActionSafetyLevel.DESTRUCTIVE, f"Destructive operation detected: '{keyword}'"


        # 3. Caution operations: form submissions, creating/updating test data
        if action in ("submit",) or ("submit" in target) or ("save" in target and action == "click"):
            return ActionSafetyLevel.CAUTION, None

        # 4. Safe operations: navigate, fill, click, select, assert
        if action in cls.SUPPORTED_ACTIONS:
            return ActionSafetyLevel.SAFE, None

        return ActionSafetyLevel.BLOCKED, f"Unsupported action type: '{action}'"

    @classmethod
    def validate_test_case(
        cls,
        test_case: TestCase,
        environment: Optional[Environment] = None,
        allow_caution: bool = True
    ) -> SafetyValidationResult:
        """
        Validates entire test case before execution.
        """
        # 1. Environment check
        if environment:
            if environment.environment_type == EnvironmentType.PROD:
                return SafetyValidationResult(
                    is_valid=False,
                    safety_level=ActionSafetyLevel.BLOCKED,
                    error_message="Autonomous execution against Production environments is prohibited by default."
                )

        # 2. Step presence check
        if not test_case.steps or len(test_case.steps) == 0:
            return SafetyValidationResult(
                is_valid=False,
                safety_level=ActionSafetyLevel.BLOCKED,
                error_message="Test case has no steps defined."
            )

        # 3. Check each step's safety and syntax
        highest_safety = ActionSafetyLevel.SAFE

        for step in test_case.steps:
            if not step.action or step.action.lower() not in cls.SUPPORTED_ACTIONS:
                return SafetyValidationResult(
                    is_valid=False,
                    safety_level=ActionSafetyLevel.BLOCKED,
                    error_message=f"Step #{step.sequence} has unsupported action: '{step.action}'"
                )

            if not step.target:
                return SafetyValidationResult(
                    is_valid=False,
                    safety_level=ActionSafetyLevel.BLOCKED,
                    error_message=f"Step #{step.sequence} is missing a target selector or URL."
                )

            level, reason = cls.classify_step(step)

            if level == ActionSafetyLevel.BLOCKED:
                return SafetyValidationResult(
                    is_valid=False,
                    safety_level=ActionSafetyLevel.BLOCKED,
                    error_message=f"Step #{step.sequence} blocked: {reason}"
                )

            if level == ActionSafetyLevel.DESTRUCTIVE:
                return SafetyValidationResult(
                    is_valid=False,
                    safety_level=ActionSafetyLevel.DESTRUCTIVE,
                    error_message=f"Step #{step.sequence} is destructive and requires manual execution approval: {reason}"
                )

            if level == ActionSafetyLevel.CAUTION:
                if not allow_caution:
                    return SafetyValidationResult(
                        is_valid=False,
                        safety_level=ActionSafetyLevel.CAUTION,
                        error_message=f"Step #{step.sequence} contains caution action and allow_caution is False."
                    )
                highest_safety = ActionSafetyLevel.CAUTION

        return SafetyValidationResult(
            is_valid=True,
            safety_level=highest_safety,
            error_message=None
        )
