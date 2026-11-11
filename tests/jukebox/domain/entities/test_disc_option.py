from jukebox.domain.entities import DiscOption


def test_default_values():
    """Should have default values for shuffle"""
    option = DiscOption()
    assert option.shuffle is False


def test_custom_values():
    """Should accept custom values"""
    option = DiscOption(shuffle=True)
    assert option.shuffle is True
