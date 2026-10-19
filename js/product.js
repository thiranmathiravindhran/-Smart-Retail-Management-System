function addProduct() {

    let name = document.getElementById("productName").value;
    let category = document.getElementById("category").value;
    let price = document.getElementById("price").value;
    let stock = document.getElementById("stock").value;
    let reorder = document.getElementById("reorder").value;

    if (name === "" || category === "" ||
        price === "" || stock === "" || reorder === "") {

        alert("Please fill all fields.");
        return;
    }

    let status;

    if (Number(stock) <= Number(reorder)) {
        status = "Low Stock";
    } else {
        status = "Available";
    }

    let table = document.getElementById("productTable");

    let row = table.insertRow();

    row.insertCell(0).innerHTML = name;
    row.insertCell(1).innerHTML = category;
    row.insertCell(2).innerHTML = "₹" + price;
    row.insertCell(3).innerHTML = stock;
    row.insertCell(4).innerHTML = status;

    document.getElementById("productForm").reset();

    alert("Product added successfully!");
}