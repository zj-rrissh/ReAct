"""WeatherTool 测试 (6 用例)。"""

import pytest
from tools.weather import WeatherTool


@pytest.fixture
def weather_tool():
    return WeatherTool()


class TestWeatherTool:
    def test_weather_returns_city_name_in_result(self, weather_tool):
        result = weather_tool.execute("北京")
        assert "北京" in result

    def test_weather_returns_temperature(self, weather_tool):
        result = weather_tool.execute("上海")
        assert "25°C" in result

    def test_weather_format(self, weather_tool):
        result = weather_tool.execute("南京")
        assert result == "南京的天气：晴，25°C"

    def test_weather_with_chinese_city_name(self, weather_tool):
        result = weather_tool.execute("深圳")
        assert "深圳" in result
        assert "晴" in result

    def test_weather_with_english_city_name(self, weather_tool):
        result = weather_tool.execute("Tokyo")
        assert "Tokyo" in result

    def test_weather_with_none_input(self, weather_tool):
        result = weather_tool.execute(None)
        assert "25°C" in result
