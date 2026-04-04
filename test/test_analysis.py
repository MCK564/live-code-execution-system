from analysis.engine import AnalyzerEngine


def test_python_analysis_detects_loop_and_division_by_zero():
    code = """
while True:
    value = 10 / 0
"""
    result = AnalyzerEngine().analyze("python", code)

    assert result.parse_error is None
    assert any(alert.kind == "infinite_loop" for alert in result.alerts)
    assert any("literal zero" in alert.message.lower() for alert in result.alerts)


def test_java_analysis_detects_unconditional_loop():
    code = """
public class Main {
    void run() {
        while (true) {
            int x = 1;
        }
    }
}
"""
    result = AnalyzerEngine().analyze("java", code)

    assert result.parse_error is None
    assert any(alert.kind == "infinite_loop" for alert in result.alerts)


def test_cpp_analysis_detects_division_by_zero():
    code = """
int main() {
    int x = 10 / 0;
    return x;
}
"""
    result = AnalyzerEngine().analyze("cpp", code)

    assert result.parse_error is None
    assert any(alert.kind == "math_risk" for alert in result.alerts)
