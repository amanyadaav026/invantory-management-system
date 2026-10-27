
const searchInput = document.getElementById("search-input");
const clearSearchButton = document.getElementById("clear-search");

clearSearchButton.addEventListener("click", function () {
    searchInput.value = "";
    searchInput.dispatchEvent(new Event("input"));
});
const productRows = document.querySelectorAll("#product-list tr");
const noResultsRow = document.createElement("tr");
noResultsRow.id = "no-results-row";
noResultsRow.innerHTML = `
    <td colspan="7" style="text-align: center;">
        No products found
    </td>
`;
noResultsRow.style.display = "none";

document.getElementById("product-list").appendChild(noResultsRow);


searchInput.addEventListener("input", applyFilters);


const sortSelect = document.getElementById("sort-products");
const productList = document.getElementById("product-list");

sortSelect.addEventListener("change", function () {
    const rows = Array.from(productList.querySelectorAll("tr"))
        .filter(row => row.cells.length === 7);

    const sortValue = sortSelect.value;

    rows.sort(function (a, b) {
        if (sortValue === "name-asc") {
            return a.cells[1].textContent.trim().localeCompare(
                b.cells[1].textContent.trim()
            );
        }

        if (sortValue === "quantity-asc") {
            return Number(a.cells[3].textContent) -
                   Number(b.cells[3].textContent);
        }

        if (sortValue === "price-asc") {
            return Number(a.cells[4].textContent.replace("₹", "")) -
                   Number(b.cells[4].textContent.replace("₹", ""));
        }

        if (sortValue === "price-desc") {
            return Number(b.cells[4].textContent.replace("₹", "")) -
                   Number(a.cells[4].textContent.replace("₹", ""));
        }

        return Number(b.cells[0].textContent) -
               Number(a.cells[0].textContent);
    });

    rows.forEach(function (row) {
        productList.appendChild(row);
    });
});

const categoryFilter = document.getElementById("category-filter");
const categoryRows = document.querySelectorAll("#product-list tr");

const categories = new Set();

categoryRows.forEach(function (row) {
    if (row.cells.length === 7) {
        const category = row.cells[2].textContent.trim();
        categories.add(category);
    }
});

categories.forEach(function (category) {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    categoryFilter.appendChild(option);
});


function applyFilters() {
    const searchValue = searchInput.value.toLowerCase().trim();
    const selectedCategory = categoryFilter.value;
    let visibleProducts = 0;

    productRows.forEach(function (row) {
        if (row.cells.length !== 7) {
            return;
        }

        const productName = row.cells[1].textContent.toLowerCase().trim();
        const productCategory = row.cells[2].textContent.trim();

        const matchesSearch =
            productName.includes(searchValue) ||
            productCategory.toLowerCase().includes(searchValue);

        const matchesCategory =
            selectedCategory === "all" ||
            productCategory === selectedCategory;

        if (matchesSearch && matchesCategory) {
            row.style.display = "";
            visibleProducts++;
        } else {
            row.style.display = "none";
        }
    });

    noResultsRow.style.display =
        visibleProducts === 0 ? "" : "none";
}

categoryFilter.addEventListener("change", applyFilters);


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