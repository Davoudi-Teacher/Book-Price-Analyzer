
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.express as px
import subprocess
import tempfile
import sys
from pathlib import Path
import textwrap
import html

# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Book Price Analyzer",
    page_icon="📚",
    layout="wide"
)

BASE_URL = "https://books.toscrape.com/"
SCRAPY_URLS = [
    "https://books.toscrape.com/catalogue/page-1.html",
    "https://books.toscrape.com/catalogue/page-2.html"
]

# --------------------------------------------------
# Custom CSS
# --------------------------------------------------

st.markdown("""
<style>
.stApp {
    background-color: #f4f6fb;
}
[data-testid="stSidebar"] {
    background-color: #172554;
}
[data-testid="stSidebar"] * {
    color: white !important;
}
.hero {
    padding: 28px;
    border-radius: 16px;
    background: linear-gradient(120deg, #172554, #2563eb);
    color: white;
    margin-bottom: 25px;
}
.hero h1 {
    color: white;
    margin-bottom: 8px;
}
.hero p {
    color: #e0e7ff;
    font-size: 17px;
}
.metric-card {
    background: white;
    border-radius: 12px;
    padding: 18px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    text-align: center;
}
.metric-label {
    color: #64748b;
    font-size: 14px;
}
.metric-value {
    color: #172554;
    font-size: 25px;
    font-weight: bold;
    margin-top: 7px;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Data preparation
# --------------------------------------------------

def prepare_data(data):
    df = pd.DataFrame(data)

    if df.empty:
        return df

    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    df = df.dropna(subset=["Title", "Price"]).reset_index(drop=True)

    return df


# --------------------------------------------------
# BeautifulSoup scraper: first page = 20 books
# --------------------------------------------------

def scrape_beautifulsoup():
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; BookPriceAnalyzer/1.0)"
    }

    response = requests.get(
        BASE_URL,
        headers=headers,
        timeout=(20, 60)
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    books = []

    for book in soup.select("article.product_pod"):
        title_element = book.select_one("h3 a")
        price_element = book.select_one("p.price_color")

        if title_element and price_element:
            title = title_element.get("title", "").strip()
            price_text = price_element.get_text(strip=True)
            price_text = price_text.replace("£", "").replace("Â", "")

            books.append({
                "Title": title,
                "Price": float(price_text),
                "Currency": "GBP",
                "Page": 1,
                "Method": "BeautifulSoup"
            })

    return prepare_data(books)


# --------------------------------------------------
# Scrapy scraper: first two pages = 40 books
# --------------------------------------------------

def scrape_scrapy():

    spider_code = '''
import scrapy

class BookSpider(scrapy.Spider):
    name = "book_spider"

    start_urls = [
        "https://books.toscrape.com/catalogue/page-1.html",
        "https://books.toscrape.com/catalogue/page-2.html"
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 0.5,
        "USER_AGENT": "Mozilla/5.0 (compatible; BookPriceAnalyzer/1.0)",
        "LOG_LEVEL": "WARNING",
        "FEED_EXPORT_ENCODING": "utf-8"
    }

    def parse(self, response):
        page_number = 1 if "page-1.html" in response.url else 2

        for book in response.css("article.product_pod"):
            title = book.css("h3 a::attr(title)").get()
            price = book.css("p.price_color::text").get()

            if title and price:
                price = price.replace("£", "").replace("Â", "").strip()

                yield {
                    "Title": title,
                    "Price": price,
                    "Currency": "GBP",
                    "Page": page_number,
                    "Method": "Scrapy"
                }
'''

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        spider_path = temp_path / "book_spider.py"
        csv_path = temp_path / "books.csv"

        spider_path.write_text(
            textwrap.dedent(spider_code),
            encoding="utf-8"
        )

        command = [
            sys.executable,
            "-m", "scrapy",
            "runspider",
            str(spider_path),
            "-O", str(csv_path),
            "-s", "ROBOTSTXT_OBEY=True",
            "-s", "DOWNLOAD_DELAY=0.5",
            "-s", "LOG_LEVEL=WARNING"
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=180
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Scrapy execution failed:\n" +
                (result.stderr or result.stdout)[-4000:]
            )

        if not csv_path.exists():
            raise RuntimeError("Scrapy did not create the CSV file.")

        df = pd.read_csv(csv_path)
        return prepare_data(df.to_dict("records"))


# --------------------------------------------------
# Statistics
# --------------------------------------------------

def show_metrics(df, method_name):
    if df.empty:
        st.warning(f"No data available for {method_name}.")
        return

    average_price = df["Price"].mean()
    minimum_price = df["Price"].min()
    maximum_price = df["Price"].max()

    col1, col2, col3, col4 = st.columns(4)

    metrics = [
        ("Number of Books", f"{len(df)}"),
        ("Average Price", f"£{average_price:.2f}"),
        ("Minimum Price", f"£{minimum_price:.2f}"),
        ("Maximum Price", f"£{maximum_price:.2f}")
    ]

    for col, (label, value) in zip(
        [col1, col2, col3, col4], metrics
    ):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.caption(f"Analysis method: {method_name}")


# --------------------------------------------------
# Charts and data table
# --------------------------------------------------

def show_analysis(df, method_name, file_name):
    if df.empty:
        return

    st.subheader("Price Analysis")

    cheapest = df.nsmallest(10, "Price")

    fig1 = px.bar(
        cheapest.sort_values("Price"),
        x="Price",
        y="Title",
        orientation="h",
        title="10 Cheapest Books",
        labels={"Price": "Price (GBP)", "Title": "Book"}
    )
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.histogram(
        df,
        x="Price",
        nbins=12,
        title="Distribution of Book Prices",
        labels={"Price": "Price (GBP)"}
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Book Dataset")

    search = st.text_input(
        f"Search books - {method_name}",
        key=f"search_{method_name}"
    )

    display_df = df.copy()

    if search:
        display_df = display_df[
            display_df["Title"].str.contains(
                search, case=False, na=False
            )
        ]

    st.dataframe(display_df, use_container_width=True)

    csv_data = df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label=f"Download {method_name} CSV",
        data=csv_data,
        file_name=file_name,
        mime="text/csv"
    )


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

st.sidebar.title("📚 Book Analyzer")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "BeautifulSoup Results",
        "Scrapy Results",
        "Method Comparison",
        "Data & Methods",
        "About Project"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("Book Price Analyzer | Python Web Scraping")


# --------------------------------------------------
# Header
# --------------------------------------------------

st.markdown("""
<div class="hero">
    <h1>📚 Book Price Analyzer</h1>
    <p>
        A web scraping and data analysis project using
        BeautifulSoup and Scrapy.
    </p>
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# Session state
# --------------------------------------------------

if "bs_books" not in st.session_state:
    st.session_state.bs_books = pd.DataFrame()

if "scrapy_books" not in st.session_state:
    st.session_state.scrapy_books = pd.DataFrame()

if "bs_error" not in st.session_state:
    st.session_state.bs_error = None

if "scrapy_error" not in st.session_state:
    st.session_state.scrapy_error = None


# --------------------------------------------------
# Refresh data
# --------------------------------------------------

if page == "Dashboard":
    st.subheader("Live Data Collection")

    st.write(
        "Run both scraping methods to collect and analyze book prices."
    )

    if st.button("🔄 Refresh Live Data", type="primary"):
        st.session_state.bs_error = None
        st.session_state.scrapy_error = None

        with st.spinner("Running BeautifulSoup..."):
            try:
                st.session_state.bs_books = scrape_beautifulsoup()
            except Exception as error:
                st.session_state.bs_error = str(error)

        with st.spinner("Running Scrapy..."):
            try:
                st.session_state.scrapy_books = scrape_scrapy()
            except Exception as error:
                st.session_state.scrapy_error = str(error)

        st.rerun()

    if st.session_state.bs_error:
        st.error("BeautifulSoup error")
        st.code(st.session_state.bs_error)

    if st.session_state.scrapy_error:
        st.error("Scrapy error")
        st.code(st.session_state.scrapy_error)

    bs_df = st.session_state.bs_books
    scrapy_df = st.session_state.scrapy_books

    st.markdown("---")
    st.subheader("Collection Overview")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### BeautifulSoup")
        st.metric("Books collected", len(bs_df))

        if not bs_df.empty:
            st.metric(
                "Average price",
                f"£{bs_df['Price'].mean():.2f}"
            )

    with col2:
        st.markdown("### Scrapy")
        st.metric("Books collected", len(scrapy_df))

        if not scrapy_df.empty:
            st.metric(
                "Average price",
                f"£{scrapy_df['Price'].mean():.2f}"
            )

    if bs_df.empty and scrapy_df.empty:
        st.info("Click Refresh Live Data to collect the books.")

    if not bs_df.empty or not scrapy_df.empty:
        st.markdown("---")
        st.subheader("Collected Data Preview")

        if not bs_df.empty:
            st.write("BeautifulSoup — first 20 books")
            st.dataframe(bs_df.head(5), use_container_width=True)

        if not scrapy_df.empty:
            st.write("Scrapy — first 40 books")
            st.dataframe(scrapy_df.head(5), use_container_width=True)


# --------------------------------------------------
# BeautifulSoup results
# --------------------------------------------------

elif page == "BeautifulSoup Results":
    st.subheader("BeautifulSoup Analysis")

    df = st.session_state.bs_books

    if df.empty:
        st.info("Please collect data from the Dashboard first.")
    else:
        show_metrics(df, "BeautifulSoup")
        show_analysis(
            df,
            "BeautifulSoup",
            "books_beautifulsoup_page1.csv"
        )


# --------------------------------------------------
# Scrapy results
# --------------------------------------------------

elif page == "Scrapy Results":
    st.subheader("Scrapy Analysis")

    df = st.session_state.scrapy_books

    if df.empty:
        st.info("Please collect data from the Dashboard first.")
    else:
        show_metrics(df, "Scrapy")
        show_analysis(
            df,
            "Scrapy",
            "books_scrapy_two_pages.csv"
        )


# --------------------------------------------------
# Comparison
# --------------------------------------------------

elif page == "Method Comparison":
    st.subheader("BeautifulSoup vs Scrapy")

    bs_df = st.session_state.bs_books
    scrapy_df = st.session_state.scrapy_books

    if bs_df.empty or scrapy_df.empty:
        st.info(
            "Please run both scraping methods from the Dashboard first."
        )
    else:
        comparison = pd.DataFrame({
            "Metric": [
                "Number of Books",
                "Average Price (GBP)",
                "Minimum Price (GBP)",
                "Maximum Price (GBP)"
            ],
            "BeautifulSoup": [
                len(bs_df),
                bs_df["Price"].mean(),
                bs_df["Price"].min(),
                bs_df["Price"].max()
            ],
            "Scrapy": [
                len(scrapy_df),
                scrapy_df["Price"].mean(),
                scrapy_df["Price"].min(),
                scrapy_df["Price"].max()
            ]
        })

        st.dataframe(comparison, use_container_width=True)

        chart_data = pd.DataFrame({
            "Method": ["BeautifulSoup", "Scrapy"],
            "Number of Books": [len(bs_df), len(scrapy_df)]
        })

        fig = px.bar(
            chart_data,
            x="Method",
            y="Number of Books",
            color="Method",
            title="Number of Books Collected by Each Method"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Average Price Comparison")

        avg_data = pd.DataFrame({
            "Method": ["BeautifulSoup", "Scrapy"],
            "Average Price": [
                bs_df["Price"].mean(),
                scrapy_df["Price"].mean()
            ]
        })

        fig2 = px.bar(
            avg_data,
            x="Method",
            y="Average Price",
            color="Method",
            title="Average Book Price by Method"
        )

        st.plotly_chart(fig2, use_container_width=True)


# --------------------------------------------------
# Data and methods
# --------------------------------------------------

elif page == "Data & Methods":
    st.subheader("Data Collection and Methodology")

    st.markdown("""
    ### 1. Data Source

    The project uses the educational website
    [Books to Scrape](https://books.toscrape.com/).

    ### 2. BeautifulSoup

    BeautifulSoup is used to extract book titles and prices
    from the first page of the website.

    - Number of pages: 1
    - Expected number of books: 20
    - Main tools: Requests and BeautifulSoup

    ### 3. Scrapy

    Scrapy is used to extract book titles and prices
    from the first two pages.

    - Number of pages: 2
    - Expected number of books: 40
    - Main tool: Scrapy framework

    ### 4. Data Analysis

    Pandas is used to organize and analyze the collected data.

    The project calculates:

    - Number of books
    - Average price
    - Minimum price
    - Maximum price

    ### 5. Visualization

    Plotly is used to create interactive charts for price analysis.
    """)


# --------------------------------------------------
# About
# --------------------------------------------------

elif page == "About Project":
    st.subheader("About This Project")

    st.markdown("""
    This project demonstrates practical applications of
    Python web scraping and data analysis.

    **Technologies used:**

    - Python
    - Requests
    - BeautifulSoup
    - Scrapy
    - Pandas
    - Streamlit
    - Plotly

    **Project objectives:**

    1. Extract book information from a website.
    2. Compare two web scraping techniques.
    3. Analyze book prices using Pandas.
    4. Visualize data through interactive charts.
    5. Publish the application as a public web dashboard.

    **Data source:** Books to Scrape
    """)

st.markdown("---")
st.caption("Book Price Analyzer | Developed with Python and Streamlit")
