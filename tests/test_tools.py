"""Araçlar (tools) modülü birim testleri."""

import unittest
from tools import file_tools, registry


class TestTools(unittest.TestCase):

    def test_registry_specs_exist(self):
        names = [spec["name"] for spec in registry.TOOL_SPECS]
        self.assertIn("web_search", names)
        self.assertIn("get_trending_topics", names)
        self.assertIn("read_file", names)
        self.assertIn("write_file", names)
        self.assertIn("get_current_datetime", names)

    def test_get_current_datetime(self):
        result = registry.run_tool("get_current_datetime", {})
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 5)

    def test_file_tools_security_sandbox(self):
        # Çalışma klasörü dışına çıkış engellenmeli
        with self.assertRaises(file_tools.ToolError):
            file_tools.read_file("../../windows/system32/cmd.exe")

    def test_file_write_and_read(self):
        filename = "test_doc.txt"
        content = "Dragon test içeriği 123"
        write_res = file_tools.write_file(filename, content)
        self.assertIn("kaydedildi", write_res)

        read_res = file_tools.read_file(filename)
        self.assertIn(content, read_res)

    def test_unknown_tool_run(self):
        res = registry.run_tool("non_existent_tool_xyz", {})
        self.assertIn("Hata", res)


if __name__ == "__main__":
    unittest.main()
