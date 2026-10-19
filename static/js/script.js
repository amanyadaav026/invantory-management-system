
const searchInput = document.getElementById("search-input");
const productRows = document.querySelectorAll("#product-list tr");

searchInput.addEventListener("input", function () {
    const searchValue = searchInput.value.toLowerCase();

    productRows.forEach(function (row) {
        const productName = row.cells[1].textContent.toLowerCase();

        if (productName.includes(searchValue)) {
            row.style.display = "";
        } else {
            row.style.display = "none";
        }
    });
});
