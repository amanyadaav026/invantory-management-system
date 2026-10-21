
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


searchInput.addEventListener("input", function () {
    const searchValue = searchInput.value.toLowerCase().trim();
    let visibleProducts = 0;

    productRows.forEach(function (row) {
        const productName = row.cells[1].textContent.toLowerCase();
        const productCategory = row.cells[2].textContent.toLowerCase();

        if (
            productName.includes(searchValue) ||
            productCategory.includes(searchValue)
        ) {
            row.style.display = "";
            visibleProducts++;
        } else {
            row.style.display = "none";
        }
    });

    noResultsRow.style.display =
        visibleProducts === 0 ? "" : "none";
});


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

