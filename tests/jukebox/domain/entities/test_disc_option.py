from discstore.domain.entities import DiscOption


def test_default_values():
    """Should have default values for shuffle and is_test"""
    option = DiscOption()
    assert option.shuffle is False
    assert option.is_test is False


def test_custom_values():
    """Should accept custom values"""
    option = DiscOption(shuffle=True, is_test=True)
    assert option.shuffle is True
    assert option.is_test is True
