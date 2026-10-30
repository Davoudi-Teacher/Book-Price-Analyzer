
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from bs4 import BeautifulSoup
from io import StringIO

# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="Book Price Analyzer",
    page_icon="📚",
    layout="wide"
)

# -----------------------------
# Custom CSS
# -----------------------------
st.markdown("""
<style>
.stApp {
    background-color: #f4f6fb;
}
section[data-testid="stSidebar"] {
    background-color: #172544;
}
section[data-testid="stSidebar"] * {
    color: white !important;
}
.main-title {
    background: linear-gradient(120deg, #243b68, #5267b8);
    padding: 30px;
    border-radius: 18px;
    color: white;
    margin-bottom: 25px;
}
.metric-card {
    background: white;
    padding: 22px;
    border-radius: 15px;
    box-shadow: 0 3px 15px rgba(0,0,0,0.06);
    text-align: center;
}
.metric-label {
    color: #65708a;
    font-size: 14px;
}
.metric-value {
    color: #243b68;
    font-size: 27px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Website settings
# -----------------------------
BASE_URL = "https://books.toscrape.com/"

# -----------------------------
# Scraping with BeautifulSoup
# -----------------------------
def scrape_books():

    all_books = []

    for page_number in range(1, 3):

        if page_number == 1:
            url = BASE_URL
        else:
            url = f"{BASE_URL}catalogue/page-{page_number}.html"

        response = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        books = soup.select("article.product_pod")

        for book in books:

            title = book.select_one("h3 a")["title"]

            price_text = book.select_one(
                "p.price_color"
            ).get_text(strip=True)

            price = float(
                price_text.replace("£", "").replace("Â", "")
            )

            all_books.append({
                "Title": title,
                "Price": price,
                "Currency": "GBP",
                "Page": page_number
            })

    return pd.DataFrame(all_books)


# -----------------------------
# Data preparation
# -----------------------------
def prepare_data(df):

    df = df.copy()

    df["Price"] = pd.to_numeric(
        df["Price"],
        errors="coerce"
    )

    df = df.dropna(subset=["Title", "Price"])

    return df


# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("📚 Book Analyzer")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Data & Methods",
        "About Project"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("Book Price Analyzer | Python Project")


# -----------------------------
# Load data
# -----------------------------
if "books" not in st.session_state:

    st.session_state.books = None

    st.session_state.error = None


# -----------------------------
# Header
# -----------------------------
st.markdown("""
<div class="main-title">
    <h1>📚 Book Price Analyzer</h1>
    <p>Web Scraping and Price Analysis Dashboard</p>
    <p>Explore book prices using Python, BeautifulSoup and Plotly</p>
</div>
""", unsafe_allow_html=True)


# -----------------------------
# Refresh button
# -----------------------------
col_refresh, col_info = st.columns([1, 3])

with col_refresh:

    if st.button(
        "🔄 Refresh Live Data",
        use_container_width=True
    ):

        try:

            with st.spinner("Collecting book data..."):

                data = scrape_books()

                data = prepare_data(data)

                st.session_state.books = data

                st.session_state.error = None

        except Exception as e:

            st.session_state.error = str(e)


with col_info:

    st.info(
        "Click Refresh Live Data to collect the latest "
        "book prices from Books to Scrape."
    )


# -----------------------------
# Display errors
# -----------------------------
if st.session_state.error:

    st.error(
        "Data collection failed: "
        + st.session_state.error
    )


# -----------------------------
# Dashboard
# -----------------------------
if page == "Dashboard":

    st.subheader("📊 Price Analysis Dashboard")

    if st.session_state.books is None:

        st.warning(
            "No data loaded yet. Click Refresh Live Data."
        )

    else:

        df = st.session_state.books

        if len(df) == 0:

            st.warning("No book records were found.")

        else:

            total_books = len(df)

            average_price = df["Price"].mean()

            minimum_price = df["Price"].min()

            maximum_price = df["Price"].max()

            # KPI Cards
            c1, c2, c3, c4 = st.columns(4)

            with c1:

                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">Total Books</div>
                        <div class="metric-value">{total_books}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with c2:

                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">Average Price</div>
                        <div class="metric-value">£{average_price:.2f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with c3:

                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">Minimum Price</div>
                        <div class="metric-value">£{minimum_price:.2f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with c4:

                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">Maximum Price</div>
                        <div class="metric-value">£{maximum_price:.2f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("---")

            # Charts
            left, right = st.columns(2)

            with left:

                st.subheader("Top 10 Cheapest Books")

                cheapest = df.nsmallest(
                    10,
                    "Price"
                ).sort_values("Price")

                fig1 = px.bar(
                    cheapest,
                    x="Price",
                    y="Title",
                    orientation="h",
                    color="Price",
                    color_continuous_scale="Blues",
                    title="Cheapest Books"
                )

                fig1.update_layout(
                    height=450,
                    yaxis_title="Book Title",
                    xaxis_title="Price (GBP)"
                )

                st.plotly_chart(
                    fig1,
                    use_container_width=True
                )

            with right:

                st.subheader("Price Distribution")

                fig2 = px.histogram(
                    df,
                    x="Price",
                    nbins=12,
                    color_discrete_sequence=["#5267b8"],
                    title="Distribution of Book Prices"
                )

                fig2.update_layout(
                    height=450,
                    xaxis_title="Price (GBP)",
                    yaxis_title="Number of Books"
                )

                st.plotly_chart(
                    fig2,
                    use_container_width=True
                )

            # Price ranges
            st.subheader("Books by Price Range")

            bins = [0, 20, 30, 40, 50, 100]

            labels = [
                "£0-20",
                "£20-30",
                "£30-40",
                "£40-50",
                "£50+"
            ]

            df_chart = df.copy()

            df_chart["Price Range"] = pd.cut(
                df_chart["Price"],
                bins=bins,
                labels=labels,
                right=False
            )

            range_counts = (
                df_chart["Price Range"]
                .value_counts()
                .reindex(labels, fill_value=0)
                .reset_index()
            )

            range_counts.columns = [
                "Price Range",
                "Number of Books"
            ]

            fig3 = px.bar(
                range_counts,
                x="Price Range",
                y="Number of Books",
                color="Number of Books",
                color_continuous_scale="Purples",
                title="Number of Books in Each Price Range"
            )

            st.plotly_chart(
                fig3,
                use_container_width=True
            )

            # Data table
            st.subheader("📖 Book Records")

            search = st.text_input(
                "Search book title"
            )

            filtered = df[
                df["Title"].str.contains(
                    search,
                    case=False,
                    na=False
                )
            ]

            st.dataframe(
                filtered.sort_values("Price"),
                use_container_width=True,
                hide_index=True
            )

            # Download
            csv_data = df.to_csv(
                index=False
            ).encode("utf-8-sig")

            st.download_button(
                "⬇️ Download CSV",
                data=csv_data,
                file_name="books_analysis.csv",
                mime="text/csv"
            )


# -----------------------------
# Data & Methods
# -----------------------------
elif page == "Data & Methods":

    st.subheader("Data Collection Methods")

    st.markdown("""
    ### 1. BeautifulSoup

    BeautifulSoup is used to extract book titles and prices
    from the Books to Scrape website.

    ### 2. Data Cleaning

    The collected prices are converted into numeric values.
    Missing records are removed.

    ### 3. Data Analysis

    The project calculates:

    - Total number of books
    - Average price
    - Minimum price
    - Maximum price

    ### 4. Data Visualization

    Plotly is used to create interactive charts.

    ### Data Source

    https://books.toscrape.com/
    """)


# -----------------------------
# About Project
# -----------------------------
elif page == "About Project":

    st.subheader("About This Project")

    st.markdown("""
    **Book Price Analyzer** is a Python web scraping
    and data analysis project.

    The main goals are:

    - Extract book information from a website.
    - Analyze book prices.
    - Visualize the results.
    - Provide an interactive dashboard.

    **Technologies:**

    - Python
    - Streamlit
    - BeautifulSoup
    - Pandas
    - Plotly
    """)

    st.markdown(
        "[Visit Books to Scrape](https://books.toscrape.com/)"
    )


# -----------------------------
# Footer
# -----------------------------
st.markdown("---")

st.caption(
    "Book Price Analyzer | Developed with Python and Streamlit"
)
