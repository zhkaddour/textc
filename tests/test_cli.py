import subprocess

def test_textc_help_works():
    result = subprocess.run(["textc", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "start" in result.stdout

def test_textc_version_works():
    result = subprocess.run(["textc", "--version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "0.1.0" in result.stdout
