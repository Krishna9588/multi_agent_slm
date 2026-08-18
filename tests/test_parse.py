from bs4 import BeautifulSoup
import markdownify

def test_html_parsing_and_markdownify():
    sample_html = """
    <html>
        <head><title>Job Portal</title><style>body { color: red; }</style></head>
        <body>
            <nav>Menu</nav>
            <h1>Python Developer</h1>
            <p>We are hiring a <b>Senior Python Engineer</b> in Pune.</p>
            <footer>Footer Links</footer>
        </body>
    </html>
    """
    soup = BeautifulSoup(sample_html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "head", "noscript", "svg", "iframe", "aside", "form"]):
        tag.decompose()

    md = markdownify.markdownify(str(soup), heading_style="ATX").strip()
    assert "Python Developer" in md
    assert "Senior Python Engineer" in md
    assert "Menu" not in md

if __name__ == "__main__":
    test_html_parsing_and_markdownify()
    print("test_parse passed.")
