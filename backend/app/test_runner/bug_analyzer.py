
import re


def analyze_bug(item: dict) -> dict:
    """
    Analyze a failed source check and return a structured bug report.
    Does not execute uploaded code.
    """

    check = str(item.get("check", "Unknown check"))
    status = str(item.get("status", "UNKNOWN"))
    details = str(item.get("details", ""))

    text = f"{check} {details}".lower()

    result = {
        "check": check,
        "status": status,
        "severity": "MEDIUM",
        "root_cause": (
            "The check failed, but the exact cause could not "
            "be identified automatically."
        ),
        "suggested_fix": (
            "Review the original error details and inspect "
            "the affected source file."
        ),
        "line_number": None,
        "confidence": "LOW",
        "bug_type": "UNKNOWN",
    }

    # Detect the reported source line, when available.
    match = re.search(r"\bline\s+(\d+)", text)
    if match:
        result["line_number"] = int(match.group(1))

    # Rule 1: Python / JavaScript / TypeScript syntax errors.
    if "syntax error" in text or "syntax:" in text:
        result["severity"] = "HIGH"
        result["confidence"] = "MEDIUM"
        result["bug_type"] = "SYNTAX_ERROR"

        if ".py" in text or "python" in text:
            result["root_cause"] = (
                "Python source contains invalid or incomplete syntax."
            )
            result["suggested_fix"] = (
                "Inspect the reported line and nearby lines. "
                "Check missing colons, parentheses, quotation marks, "
                "function definitions, and indentation."
            )
        else:
            result["root_cause"] = (
                "JavaScript, TypeScript, or JSX source contains "
                "invalid syntax."
            )
            result["suggested_fix"] = (
                "Inspect the reported line and nearby lines. "
                "Check brackets, braces, parentheses, quotation marks, "
                "JSX tags, and missing separators."
            )

    # Rule 2: Invalid package.json.
    elif "package.json" in text or "jsondecodeerror" in text:
        result["severity"] = "HIGH"
        result["confidence"] = "MEDIUM"
        result["bug_type"] = "INVALID_MANIFEST"
        result["root_cause"] = (
            "The package manifest contains invalid JSON."
        )
        result["suggested_fix"] = (
            "Check commas, double quotes, braces, and brackets. "
            "Ensure package.json contains a valid JSON object."
        )

    # Rule 3: File size limit.
    elif "exceeds the 1 mb" in text:
        result["severity"] = "LOW"
        result["confidence"] = "HIGH"
        result["bug_type"] = "FILE_SIZE_LIMIT"
        result["root_cause"] = (
            "The file exceeds the configured source-check size limit."
        )
        result["suggested_fix"] = (
            "Review the file size and safe-check configuration."
        )

    # Rule 4: Missing Babel parser.
    elif "babel parser was not found" in text:
        result["severity"] = "MEDIUM"
        result["confidence"] = "HIGH"
        result["bug_type"] = "MISSING_PARSER"
        result["root_cause"] = (
            "The required Babel parser dependency was not found."
        )
        result["suggested_fix"] = (
            "Verify that @babel/parser is installed in the frontend "
            "dependencies and that the configured path is correct."
        )

    # Rule 5: Timeout.
    elif "timeout" in text or "timed out" in text:
        result["severity"] = "MEDIUM"
        result["confidence"] = "MEDIUM"
        result["bug_type"] = "TIMEOUT"
        result["root_cause"] = (
            "The source-check operation exceeded its time limit."
        )
        result["suggested_fix"] = (
            "Inspect the affected file and parser setup, then retry."
        )

    # Rule 6: Python import errors.
    elif (
        "modulenotfounderror" in text
        or "no module named" in text
        or "importerror" in text
    ):
        result["severity"] = "HIGH"
        result["confidence"] = "MEDIUM"
        result["bug_type"] = "IMPORT_ERROR"
        result["root_cause"] = (
            "A required Python module could not be imported."
        )
        result["suggested_fix"] = (
            "Verify the import name, install the required dependency "
            "in the intended environment, and check the Python path."
        )

    # Rule 7: Undefined names or variables.
    elif (
        "nameerror" in text
        or "is not defined" in text
        or "undefined variable" in text
    ):
        result["severity"] = "HIGH"
        result["confidence"] = "MEDIUM"
        result["bug_type"] = "UNDEFINED_NAME"
        result["root_cause"] = (
            "The code references a name or variable that may not "
            "be defined in the current scope."
        )
        result["suggested_fix"] = (
            "Check the spelling, declaration, imports, and scope "
            "of the referenced name before using it."
        )

    # Rule 8: Attribute errors.
    elif "attributeerror" in text or "has no attribute" in text:
        result["severity"] = "MEDIUM"
        result["confidence"] = "MEDIUM"
        result["bug_type"] = "ATTRIBUTE_ERROR"
        result["root_cause"] = (
            "The code attempted to access an attribute that may not "
            "exist on the object or value."
        )
        result["suggested_fix"] = (
            "Check the object's type, attribute name, and whether "
            "the expected object was returned."
        )

    # Rule 9: Type errors.
    elif "typeerror" in text:
        result["severity"] = "MEDIUM"
        result["confidence"] = "MEDIUM"
        result["bug_type"] = "TYPE_ERROR"
        result["root_cause"] = (
            "An operation may be using an incompatible data type "
            "or an invalid number of arguments."
        )
        result["suggested_fix"] = (
            "Check the values and argument types passed to the "
            "operation and validate inputs before processing."
        )

    # Rule 10: Assertion or test failures.
    elif "assertionerror" in text or "assertion failed" in text:
        result["severity"] = "HIGH"
        result["confidence"] = "MEDIUM"
        result["bug_type"] = "ASSERTION_FAILURE"
        result["root_cause"] = (
            "An assertion or expected test condition did not pass."
        )
        result["suggested_fix"] = (
            "Compare the actual result with the expected result and "
            "check the test inputs and application logic."
        )

    return result
