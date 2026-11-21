
/* Step 7: Server-side Product Filters */

const filterForm = document.getElementById("product-filter-form");
const searchInput = document.getElementById("search-input");
const clearSearchButton = document.getElementById("clear-search");
const categoryFilter = document.getElementById("category-filter");
const sortSelect = document.getElementById("sort-products");

if (filterForm) {

    let searchTimer;

    // Live Search with debounce
    searchInput.addEventListener("input", function () {
        clearTimeout(searchTimer);

        searchTimer = setTimeout(function () {
            filterForm.submit();
        }, 400);
    });

    // Search immediately when Enter is pressed
    searchInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            clearTimeout(searchTimer);
            filterForm.submit();
        }
    });

    // Category filtering
    categoryFilter.addEventListener("change", function () {
        filterForm.submit();
    });

    // Sorting
    sortSelect.addEventListener("change", function () {
        filterForm.submit();
    });

    // Clear all filters
    clearSearchButton.addEventListener("click", function () {
        clearTimeout(searchTimer);

        searchInput.value = "";
        categoryFilter.value = "all";
        sortSelect.value = "default";

        filterForm.submit();
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