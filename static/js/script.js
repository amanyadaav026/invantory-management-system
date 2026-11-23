
/* Day 10: AJAX Product Filters */

const filterForm = document.getElementById("product-filter-form");
const searchInput = document.getElementById("search-input");
const clearSearchButton = document.getElementById("clear-search");
const categoryFilter = document.getElementById("category-filter");
const sortSelect = document.getElementById("sort-products");

const productList = document.getElementById("product-list");
const paginationContainer = document.getElementById("pagination-container");
const resultCountElement = document.getElementById("product-result-count");
if (
    filterForm &&
    searchInput &&
    categoryFilter &&
    sortSelect &&
    productList &&
    paginationContainer
) {
    let searchTimer;

    async function loadProducts(page = 1, historyMode = "replace") {
        const url = new URL(filterForm.action, window.location.origin);

        url.searchParams.set("page", page);
        url.searchParams.set("search", searchInput.value.trim());
        url.searchParams.set("category", categoryFilter.value);
        url.searchParams.set("sort", sortSelect.value);
        url.hash = "product-list";

        if (historyMode === "push") {
            window.history.pushState({}, "", url);
        } else if (historyMode === "replace") {
            window.history.replaceState({}, "", url);
        }

        productList.setAttribute("aria-busy", "true");

        try {
            const response = await fetch(
                url.pathname + url.search,
                {
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    }
                }
            );

            if (!response.ok) {
                throw new Error("Unable to load products.");
            }

            const data = await response.json();

            productList.innerHTML = data.rows_html;
            paginationContainer.innerHTML = data.pagination_html;
            if (resultCountElement) {
                resultCountElement.textContent =
                `${data.result_count} matching products`;
            }

        } catch (error) {
            console.error("AJAX Search Error:", error);
        } finally {
            productList.removeAttribute("aria-busy");
        }
    }

    // Live search with debounce
    searchInput.addEventListener("input", function () {
        clearTimeout(searchTimer);

        searchTimer = setTimeout(function () {
            loadProducts(1, "replace");
        }, 350);
    });

    // Prevent normal form submission
    filterForm.addEventListener("submit", function (event) {
        event.preventDefault();

        clearTimeout(searchTimer);
        loadProducts(1, "replace");
    });

    // Category filtering
    categoryFilter.addEventListener("change", function () {
        clearTimeout(searchTimer);
        loadProducts(1, "push");
    });

    // Sorting
    sortSelect.addEventListener("change", function () {
        clearTimeout(searchTimer);
        loadProducts(1, "push");
    });

    // Clear all filters
    if (clearSearchButton) {
        clearSearchButton.addEventListener("click", function () {
            clearTimeout(searchTimer);

            searchInput.value = "";
            categoryFilter.value = "all";
            sortSelect.value = "default";

            loadProducts(1, "push");
        });
    }

    // AJAX pagination
    paginationContainer.addEventListener("click", function (event) {
        const paginationLink = event.target.closest("a.pagination-button");

        if (!paginationLink) {
            return;
        }

        event.preventDefault();

        const pageUrl = new URL(paginationLink.href);
        const nextPage = Number(pageUrl.searchParams.get("page"));

        if (nextPage) {
            loadProducts(nextPage, "push");
        }
    });

    // Browser Back and Forward support
    window.addEventListener("popstate", function () {
        const params = new URLSearchParams(window.location.search);

        searchInput.value = params.get("search") || "";
        categoryFilter.value = params.get("category") || "all";
        sortSelect.value = params.get("sort") || "default";

        const page = Number(params.get("page")) || 1;

        loadProducts(page, "none");
    });
}

/* Step 6: Stock Overview Progress Bars */

document.querySelectorAll(".stock-progress-fill").forEach(bar => {
    const count = Number(bar.dataset.count);
    const total = Number(bar.dataset.total);

    const percentage = total > 0
        ? (count / total) * 100
        : 0;

    bar.style.width = `${percentage}%`;
});


/* ========================================
   Step 8: Dynamic Sidebar Navigation
======================================== */

const sidebarLinks = document.querySelectorAll(".sidebar-nav .nav-link");

function updateActiveLink(activeLink) {
    sidebarLinks.forEach(function (link) {
        link.classList.remove("active");
    });

    activeLink.classList.add("active");
}

sidebarLinks.forEach(function (link) {
    link.addEventListener("click", function () {
        updateActiveLink(link);
    });
});
/* ========================================
   StockTrack Dashboard Charts
======================================== */

document.addEventListener("DOMContentLoaded", function () {
    const valueCanvas = document.getElementById("inventoryValueChart");
    const distributionCanvas = document.getElementById("stockDistributionChart");

    // Stop if the chart containers are not on this page
    if (!valueCanvas || !distributionCanvas) {
        return;
    }

    // Read chart data passed from Flask through the HTML
    const analyticsDataElement = document.getElementById("analytics-chart-data");

    if (!analyticsDataElement) {
        return;
    }

    const analyticsData = JSON.parse(analyticsDataElement.textContent);
    const categories = analyticsData.map(item => item.category);
    const inventoryValues = analyticsData.map(item => item.inventory_value);
    const quantities = analyticsData.map(item => item.total_quantity);

    // Inventory Value Chart
    new Chart(valueCanvas, {
        type: "bar",
        data: {
            labels: categories,
            datasets: [{
                label: "Inventory Value (₹)",
                data: inventoryValues,
                backgroundColor: "#2563eb",
                borderRadius: 6,
                maxBarThickness: 48
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    // Stock Distribution Chart
    new Chart(distributionCanvas, {
        type: "doughnut",
        data: {
            labels: categories,
            datasets: [{
                label: "Total Quantity",
                data: quantities,
                backgroundColor: [
                    "#2563eb",
                    "#14b8a6",
                    "#f59e0b",
                    "#8b5cf6",
                    "#ec4899",
                    "#64748b",
                    "#22c55e",
                    "#f97316"
                ],
                borderWidth: 2,
                borderColor: "#ffffff"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom"
                }
            }
        }
    });
});