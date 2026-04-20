import pytest
from lxml import html

# XPaths copied from scripts/apec.py
XPATH_APPLY_LINK = "//a[contains(normalize-space(.), 'Postuler') and contains(@class, 'btn')]"
XPATH_MODAL_POSTULER = "//button[contains(normalize-space(.), 'Postuler')]"
XPATH_MODAL_SEND = "//button[contains(normalize-space(.), 'Envoyer ma candidature')]"

def test_apply_link_selector():
    mock_html = """
    <div>
        <a class="btn btn-primary" href="#">Postuler</a>
        <a class="btn" href="#">  Postuler  </a>
        <button class="btn">Postuler</button>
    </div>
    """
    tree = html.fromstring(mock_html)
    results = tree.xpath(XPATH_APPLY_LINK)
    assert len(results) == 2
    assert results[0].text.strip() == "Postuler"

def test_modal_postuler_selector():
    mock_html = """
    <div class="modal">
        <button title="Postuler">Postuler</button>
        <button>  Postuler  </button>
    </div>
    """
    tree = html.fromstring(mock_html)
    results = tree.xpath(XPATH_MODAL_POSTULER)
    assert len(results) == 2

def test_modal_send_selector():
    mock_html = """
    <div class="modal">
        <button>Envoyer ma candidature</button>
        <button>  Envoyer ma candidature  </button>
    </div>
    """
    tree = html.fromstring(mock_html)
    results = tree.xpath(XPATH_MODAL_SEND)
    assert len(results) == 2

def test_didomi_id():
    # This is just a string check but we can verify it exists in a mock
    mock_html = '<button id="didomi-notice-agree-button">Accept</button>'
    tree = html.fromstring(mock_html)
    results = tree.xpath("//button[@id='didomi-notice-agree-button']")
    assert len(results) == 1
