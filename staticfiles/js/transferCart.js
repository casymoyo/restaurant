let cart = [];

function addItem(productId, fromBranchId, toBranchId, quantity, price) {
  const existingItem = cart.find((item) => item.product.id === productId);

  if (existingItem) {
    existingItem.quantity += quantity;
  } else {
    // Assuming you can fetch product/branch names dynamically
    const newTransfer = {
      product:productId, 
      from_branch: fromBranchId,
      to_branch:toBranchId,
      quantity: quantity,
      price:price
    };
    cart.push(newTransfer);
  }

  updateCartDisplay(); // You'll need to implement this
}

function removeItem(productId) {
  cart = cart.filter((item) => item.product.id !== productId);
  updateCartDisplay();
}

function processCart() {
  fetch("/process-transfer-cart/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"), // Get CSRF token
    },
    body: JSON.stringify(cart),
  })
    .then((response) => {
      if (response.ok) {
        cart = []; // Clear cart
        updateCartDisplay();
        // Display success message
      } else {
        // Handle error 
      }
    })
    .catch((error) => {
      console.error("Error:", error);
    });
}

// Helper - Get CSRF Token (adjust if needed)
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
