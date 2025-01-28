import unittest
from playwright.sync_api import sync_playwright


class TestFrontend(unittest.TestCase):
    """Frontend test cases for the Log Investigation Bot."""

    def setUp(self):
        """Set up the Playwright browser and page."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)  # Set headless=True for CI environments
        self.page = self.browser.new_page()
        self.page.goto("http://localhost:8501")  # Update URL if needed

    def tearDown(self):
        """Clean up the browser and Playwright instance."""
        self.browser.close()
        self.playwright.stop()

    def test_upload_valid_file_and_analyze(self):
        """Test uploading a valid file and performing basic analysis."""
        # Upload a valid log file
        self.page.set_input_files("input[type='file']", "test_valid.log")

        # Click "Basic Analyze"
        self.page.click("text=Basic Analyze")

        # Wait for the results
        self.page.wait_for_selector("text=Error Summary")

        # Verify results
        self.assertTrue(self.page.is_visible("text=Error Summary"))
        print("Test Passed: Valid file upload and basic analysis.")

    def test_invalid_file_upload(self):
        """Test uploading an invalid file type."""
        # Upload an invalid file type
        self.page.set_input_files("input[type='file']", "test_invalid.jpg")

        # Verify error message
        self.assertTrue(self.page.is_visible("text=Invalid file type"))
        print("Test Passed: Invalid file upload.")

    def test_analyze_no_errors(self):
        """Test analyzing a log file with no errors."""
        # Upload a log file with no errors
        self.page.set_input_files("input[type='file']", "test_no_errors.log")

        # Click "Basic Analyze"
        self.page.click("text=Basic Analyze")

        # Wait for the message
        self.page.wait_for_selector("text=No errors found in the log file.")

        # Verify results
        self.assertTrue(self.page.is_visible("text=No errors found in the log file."))
        print("Test Passed: No errors found in the log file.")

    def test_ai_summary(self):
        """Test summarizing a log file using AI."""
        # Upload a valid log file
        self.page.set_input_files("input[type='file']", "test_valid.log")

        # Click "AI Summary"
        self.page.click("text=AI Summary")

        # Wait for the summary to load
        self.page.wait_for_selector("text=Log Summary")

        # Verify summary is displayed
        self.assertTrue(self.page.is_visible("textarea[key='log_summary']"))
        print("Test Passed: AI Summary displayed.")

    def test_query_ai____(self):
        """Test querying AI with a valid query."""
        # Upload a valid log file
        self.page.set_input_files("input[type='file']", "test_valid.log")

        # Enter a query
        self.page.fill("input[placeholder='Enter your query here...']", "What is the most common error?")

        # Click "Query AI"
        self.page.click("text=Query AI")

        # Wait for the AI response
        self.page.wait_for_selector("textarea[key='ai_response']")

        # Verify response is displayed
        self.assertTrue(self.page.is_visible("textarea[key='ai_response']"))
        print("Test Passed: AI response displayed.")

    def test_query_ai(self):
        """Test querying AI with a valid query."""
        # Upload a valid log file
        self.page.set_input_files("input[type='file']", "test_valid.log")

        # Enter a query
        self.page.fill("input[placeholder='Enter your query here...']", "What is the most common error?")

        # Click "Query AI"
        self.page.click("text=Query AI")

        # Debugging: Take a screenshot and print the page content
        self.page.screenshot(path="debug_query_ai.png")
        print(self.page.content())

        # Wait for the AI response
        try:
            self.page.wait_for_selector("textarea[key='ai_response']", timeout=60000)  # Increased timeout
            assert self.page.is_visible("textarea[key='ai_response']")
            print("Test Passed: AI response displayed.")
        except Exception as e:
            print(f"Error during test: {e}")
            raise e


