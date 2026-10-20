
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

