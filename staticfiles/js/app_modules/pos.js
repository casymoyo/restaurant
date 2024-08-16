
let cart = [];
let data = [];
let respData = [];
let currencyData = [];
const customersData = [];
let customerBalanceData = []

let discount_amount = 0;
let delivery_amount = 0;
let payable_amount = 0;
let vat_amount = 0;
let amount_paid = 0;
let paymentMethod = 'cash'

let error = document.querySelector('#error_message')

const currencySelect = document.querySelector('#currency')
const endOfDayModal = new bootstrap.Modal(document.getElementById('endOfDayModal'));
const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
const receiptModal = new bootstrap.Modal(document.getElementById('receiptModal'));
const loaderModal = new bootstrap.Modal(document.getElementById('loaderModal'));
const qouteModal = new bootstrap.Modal(document.getElementById('qouteModal'));

const customerModal = new bootstrap.Modal(document.getElementById('customerModal'));

document.querySelector('#end').addEventListener(
    'click', ()=>{
        endOfDayModal.show()
    }
)

currencySelect.addEventListener(
    'change', ()=>{
        const data = {id:currencySelect.value}
        $.ajax({
            url: '{% url "finance:currency_json" %}',
            type: 'GET',
            data: data,
            }).done(function(response) {
                const data = response
                console.log(data)
                currencyData = []
                currencyData.push(data)
        })
    }
)

//credit
const cashBtn = document.querySelector('#id_cash_btn')
const bankBtn = document.querySelector('.bank')
const ecocash= document.querySelector('.ecocash')


// modals
const overlay = document.querySelector(".overlay");
const modal = document.querySelector('.payment-modal');
const clientModal = new bootstrap.Modal(document.querySelector('#clientModal'));
const closeModalBtn = document.querySelectorAll(".btn-close");
const closebtn = document.querySelector('.closebtn')

closebtn.addEventListener('click', ()=>{
    modal.add.classList('hidden')
})


document.querySelector('#id_pay').addEventListener(
    'click', ()=>{
        
        if($('#search-input').val()){
            updateCartDisplay();
            updateOrderDisplay() 
            modal.classList.remove("hidden");
            overlay.classList.remove("hidden");
        }else{
            errorModal.classList.remove('hidden')
            overlay.classList.remove('hidden')
            error.textContent=''
            error.textContent='Wasirira Mutengi'
        }
    }
)

document.querySelector('#id_add_client').addEventListener(
    'click',()=>{
        clientModal.show()
    }
)

closeModalBtn.forEach((btn)=>{
    btn.addEventListener(
        'click', ()=>{
            clientModal.classList.add('hidden')
            modal.classList.add("hidden");
            overlay.classList.add("hidden");
        }
    )
})

//search filters and fetching data
const productListContainer = document.getElementById('product-list');
const categorySelect = document.getElementById('id_category');
const search = document.getElementById('id_search')

//const loader = document.getElementById('loader').style.display = 'block';

search.addEventListener('input', ()=>{
    fetchData(search.value)
})
   
categorySelect.addEventListener('change', function() {
    const selectedCategoryId = this.value;
    fetchData(parseInt(selectedCategoryId))
});

async function fetchData (param){

    let url = '/inventory/product/list/';

    if (typeof param ==="number" & param !== 0) {
        url += `?category=${param}`; 
    }else if (typeof param === "string"){
        url += `?q=${param}`; 
    }
   
    try {
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error('Network response was not ok.');
        }
        const products = await response.json();
        productListContainer.innerHTML = ''; 
        
        displayProducts(products);
        
    } catch (error) {
        console.error('Error fetching products:', error);
        productListContainer.innerHTML = '<p class="error-message">Error loading products. Please try again later.</p>';
    } finally {
    }
}

fetchData()

function cartButton(){
    const cartBtn = document.querySelector('#id_pay')
    if(cart.length==0){
        cartBtn.disabled = true
    }else{
        cartBtn.disabled = false
    }
}

cartButton()

function displayProducts(products){

    products.forEach(product => {
       
        const productDiv = document.createElement('div');
        productDiv.className = 'col-3 mb-3';
        const outOfStock = product.quantity <= 0 ? 'Out of Stock': ''
        productDiv.innerHTML = `
        <div class="card" id='id_product_card' data-product=${product}>
            <div class="card-body d-flex flex-column align-items-center justify-content-center">
            <div class="d-flex align-items-center">
                <i style="font-size:40px" class='bx bx-barcode'></i>
            </div>
            <p class="px-1 fw-bold">${product.product_name}</p>
            <small class="px-1 text-muted">${product.description}</small>
            <p class="px-1 fw-bold">${outOfStock}</p>
            </div>
            <div class="mt-1">
            <button id="id_add_to_cart" class="w-100 btn btn-light btn-sm" data-product=${product.inventory_id} onclick='fetchProductData(this)' >
                <i class="bx bx-plus"></i> Add to cart
            </button>
            </div>
        </div>
        `;
        productListContainer.appendChild(productDiv);
    });
}

// Cart 
async function fetchProductData (product){
    if  ($('#currency').val()){
        const id = product.dataset.product

        let url = `/inventory/product/list/?product=${id}`;

        try {
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error('Network response was not ok.');
            }
            const product = await response.json();
            addItem(product)
            
        } catch (error) {
            console.error('Error fetching products:', error);
            productListContainer.innerHTML = '<p class="error-message">Error loading products. Please try again later.</p>';
        } finally {
        }
    }else{
        errorModal.show()
        error.textContent=''
        error.textContent=`Choose Currency`
    }
    
}

function generateUniqueId() {
    return Math.floor(Math.random() * 1000000000).toString(36);
  }

function addItem(product) {
    const existingItem = cart.find((item) => item.inventory_id === product[0].inventory_id)

    if (existingItem) {
        existingItem.quantity += 1;
    } else {
        const newTransfer = {
        id:generateUniqueId(),
        inventory_id:product[0].inventory_id, 
        product_name: product[0].product_name,
        quantity:1,
        price:`${product[0].price * parseFloat(currencyData[0][0]?.exchange_rate)}`
        };
        cart.push(newTransfer);
    }
    updateCartDisplay(); 
    updateOrderDisplay()
    cartButton()
    totals()
}

function totals(){

    let totalAmount = calculateTotalAmount(cart);
    let vatAmount = calculateVAT(totalAmount);
    let discount = $('#id_discount').val()
    let delivery = parseFloat($('#id_dc_input').val())
    
    let payable = totalAmount + vatAmount + delivery;
    
    // validate for not a number
    if (delivery >= 0){
        delivery = delivery
    }else{delivery = 0}

    delivery_amount = delivery
    vat_amount = vatAmount

    if(discount === 0){
        document.getElementById("id_total_amount").textContent = `${ currencyData[0][0].symbol + ' ' + totalAmount.toFixed(2)}`;
        document.getElementById("id_vat_amount").textContent =`${ currencyData[0][0].symbol + ' ' + vatAmount.toFixed(2)}`;
        document.getElementById('id_payable').textContent = `${ currencyData[0][0].symbol + ' ' + payable.toFixed(2)}`;

        payable_amount = payable
        discount_amount = discount

        updateTfoot(vatAmount, totalAmount, discountAmount, discount, delivery, payable)

    }else{
        totalAmount = totalAmount - discount
        console.log(totalAmount)
        discountAmount = calculateTotalAmount(cart) - totalAmount
        vatAmount = totalAmount * 0.15
        payable = totalAmount + vatAmount + delivery;
        console.log(totalAmount, vatAmount,  delivery, payable)
        
        vat_amount = vatAmount
        payable_amount = payable
        discount_amount = discountAmount

        document.getElementById("id_total_amount").textContent = `${ currencyData[0][0].symbol + ' ' + totalAmount.toFixed(2)}`;
        document.getElementById("id_vat_amount").textContent =`${ currencyData[0][0].symbol + ' ' + vatAmount.toFixed(2)}`;
        document.getElementById('id_payable').textContent = `${ currencyData[0][0].symbol + ' ' + payable.toFixed(2)}`;

        updateTfoot(vatAmount, totalAmount, discountAmount, discount, delivery, payable)
    }
}

function calculateTotalAmount(cart) {
   let total = cart.reduce((total, item) => total + item.price * item.quantity, 0);
   return total.toFixed(2)
}

function calculateVAT(totalAmount) {
    const vatRate = 0.15; 
    return totalAmount * vatRate;
}

// events for discount and delivery charge
document.querySelector('#id_discount').addEventListener(
    'input', ()=>{
        totals()
    }
)

document.querySelector('#id_dc_input').addEventListener(
    'input', ()=>{
        totals()
    }
)

function updateCartDisplay() {
    const cartItemsList = document.getElementById("cart_items");
    cartItemsList.innerHTML = ""; 
  
    let total = 0;
    cart.forEach((item) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>
            <small class='bx bx-trash-alt text-danger' data-id=${item.id} onclick="removeItem(this);"></small>
            <small class='bx bx-chevron-up fw-bold text-success'></small>
            <small class='bx bx-chevron-down fw-bold text-danger'></small>
            ${item.quantity}
        </td>
        <td>${item.product_name}</td>
        <td>${ currencyData[0][0].symbol + ' ' + parseFloat(item.price).toFixed(2)}</td>
        <td>${currencyData[0][0].symbol + ' ' + (parseInt(item.quantity) * parseFloat(item.price)).toFixed(2)}</td>
      `;
      cartItemsList.appendChild(row);
    });
  }

function updateOrderDisplay() {
    const orderDetails = document.getElementById("order_details");
    orderDetails.innerHTML = ""; 
  
    let total = 0;
    cart.forEach((item) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${item.product_name} x ${item.quantity}</td>
        <td class='d-flex justify-content-end'>${currencyData[0][0].symbol + ' ' + (parseInt(item.quantity) * parseFloat(item.price)).toFixed(2)}</td>
      `;
      orderDetails.appendChild(row);
    });
  }

// update tfoot
function updateTfoot(vat, totalAmount, discountAmount, discount, delivery, payable){
    document.querySelector('#id_subtotal').textContent = `${ currencyData[0][0].symbol + ' ' + calculateTotalAmount(cart)}`
    document.querySelector('#id_vat').textContent = `${ currencyData[0][0].symbol + ' ' + vat.toFixed(2)}`
    document.querySelector('#id_dcp').textContent = `Discount`
    document.querySelector('#id_disc').textContent = `${ currencyData[0][0].symbol + ' ' + '<span class="disc_c">' + discountAmount.toFixed(2) + '</span>'}`
    document.querySelector('#id_delivery_charge').textContent = `${ currencyData[0][0].symbol + ' ' + '<span class="d_c">' + delivery.toFixed(2) + "</span>"}`
    document.querySelector('#id_interest_amount').textContent = `${ currencyData[0][0].symbol + ' ' +  '<span class="inter">' + 0.00 + "</span>"}`
    document.querySelector('#id_due_amount').textContent = `${ currencyData[0][0].symbol + ' ' + payable.toFixed(2)}`
    document.querySelector('#id_balance').textContent = `${ currencyData[0][0].symbol + ' ' + (payable.toFixed(2) - amount_paid.toFixed(2))}` // payable + due amount - paid amount
}

// pay amount event
document.querySelector('#id_amount_paid').addEventListener(
    'input', ()=>{
        amount_paid = parseFloat($('#id_amount_paid').val())
        document.querySelector('#id_paid_amount').textContent = `${currencyData[0][0].symbol + ' ' +  amount_paid.toFixed(2)}`
        totals()
    }
)

const removeItem = (el) => {
    const id = el.dataset.id
    cart = cart.filter((item) => item.id !== id);
    updateCartDisplay();
    cartButton()
    totals()
}

// payment methods
document.querySelectorAll('.pm').forEach(button => {
    button.addEventListener('click', () => {
        if (button.dataset.name === 'cash') { 
            paymentMethod = button.dataset.name;
        } else if (button.dataset.name === 'ecocash'){
            paymentMethod = button.dataset.name;
        } else if (button.dataset.name === 'bank'){
            paymentMethod = button.dataset.name;
        }else if (button.dataset.name === 'paylater'){
            paymentMethod = button.dataset.name;
        }
    });
});

// processing the product cart
function processCart(el) {
    data = [
        {
            subtotal:calculateTotalAmount(cart),
            currency:currencyData[0][0].id,
            amount_paid:amount_paid,
            client_id:$('#search-input').val(),
            days: $('#id_days').val(),
            note: $('#id_note').val(),
            discount:discount_amount,
            delivery:delivery_amount,
            payable:payable_amount,
            vat_amount:vat_amount,
            payment_method:paymentMethod,
        }
    ]

    if(el.dataset.name === 'pay_later'){
        console.log('here', data[0]?.days)
        if(data[0]?.days <= 0){
            document.querySelector('#pay_error').textContent='* Please enter the credit days';
            document.querySelector('#id_days').focus();
            return
        }
    }

    if (el.dataset.name == 'qoutation'){
        fetch("{% url 'finance:add_qoutation' %}", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"), 
            },
            body: JSON.stringify({
                data: data,
                items: cart
            }),
        })
        .then(response => response.json())
        .then(data => {
            console.log(data)
            if (data.success) {
                cart = [];
                updateCartDisplay();
                qouteModal.show()
                modal.classList.add('hidden')
                overlay.classList.add('hidden')
                setTimeout(() => {
                    qouteModal.hide()
                    window.location.href=`/finance/qoutation/preview/${data.qoute_id}`
                    
                }, 2000); 
            } else {
                console.log('error')
            }
        })
        .catch(error => {
            console.error("Error during request:", error.message);
        })
    }else{
        fetch("{% url 'finance:create_invoice' %}", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"), 
            },
            body: JSON.stringify({
                data: data,
                items: cart
            }),
        })
        .then(response => response.json())
        .then(data => {
            console.log(data)
            if (data.success) {
                cart = [];
                updateCartDisplay();
                displayReceipt(data.invoice_id)
            } else {
                //put error modal
            }
        })
        .catch(error => {
            console.error("Error during request:", error.message);
        })
    }
    
};


function displayReceipt(invoiceId) {
    fetch(`/finance/invoice/preview/json/${invoiceId}/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
    })
      .then((response) => response.json())
      .then((data) => {
        console.log(data)
        const invoiceNumber = data.invoice.invoice_number;
        const invoiceItems = data.invoice_items;
        const invoiceTotal = data.invoice.amount;
        const deliveryCharge = data.invoice.delivery_charge;
        const discountAmount = data.invoice.discount_amount;
        const vatAmount = data.invoice.vat;
        const subTotal = data.invoice.subtotal;
        const currencySymbol = data.invoice.currency_symbol; 
  
        
        document.querySelector('#receiptNumber').textContent = invoiceNumber;
  
       
        const receiptTableBody = document.querySelector('#receiptTable');
        receiptTableBody.innerHTML = '';
  
        // Populate the table with invoice items
        invoiceItems.forEach((item) => {
          const newRow = receiptTableBody.insertRow();
          newRow.insertCell().textContent = item.quantity;
          newRow.insertCell().textContent = `${item.item__product__name} (${item.item__product__description})`; 
          newRow.insertCell().textContent = `${currencySymbol} ${item.total_amount}`;
        });
  
        // Update total amounts in the footer
        document.querySelector('#subTotalAmount').textContent = `${currencySymbol} ${subTotal}`;
        document.querySelector('#totalAmount').textContent = `${currencySymbol} ${invoiceTotal}`;
        document.querySelector('#deliveryChargeAmount').textContent = `${currencySymbol} ${deliveryCharge}`;
        document.querySelector('#discountAmount').textContent = `${currencySymbol} ${discountAmount}`;
        document.querySelector('#vatAmount').textContent = `${currencySymbol} ${vatAmount}`;
  
        modal.classList.add("hidden");
        overlay.classList.add("hidden");

        loaderModal.show();
        
        setTimeout(() => {
          loaderModal.hide();  
          receiptModal.show()
        }, 2000); 

      })
      .catch((error) => {
        console.error("Error:", error);
        loaderModal.hide();
      });
  }
  
// customer get and post
function submitClient(){
    const data = {
        name: $('#id_name').val(),
        email: $('#id_email').val(),
        phonenumber: $('#id_phonenumber').val(),
        address: $('#id_address').val()
    }

    fetch("{% url 'finance:add_customer' %}", {
        method: "POST",
        headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"), 
        },
        body: JSON.stringify(data),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            clientModal.hide()
            customerModal.show()
            fetchCustomers()

        } else {
            document.querySelector('#id_client_error').textContent= '*' + data.message
        }
    })
    .catch((error) => {
    console.error("Error:", error);
    });

}

async function fetchCustomers(){
    try {
        const response = await fetch('{% url "finance:customers" %}');

        if (!response.ok) {
            throw new Error('Network response was not ok.');
        }
        const customers = await response.json();

        customersData.push(customers)
        
        displayCustomers(customers);
    } catch (error) {
        console.error('Error fetching products:', error);
        productListContainer.innerHTML = '<p class="error-message">Error loading products. Please try again later.</p>';
    } finally {

        //loader.style.display = 'none';
    }
}
fetchCustomers()


function displayCustomers(customers){
    const cusElement = document.querySelector('#search-input')
    
    while(cusElement.options.length > 1){
        cusElement.remove(1)
    }
    customers.forEach((customer)=>{
        cusElement.innerHTML += `<option value=${customer.id}>${customer.name}</option>`
    })
}

document.querySelector('#search-input').addEventListener(
    'change',()=>{
        fetchCustomerAccount(document.querySelector('#search-input').value)
    }
)

async function fetchCustomerAccount(customerId){
    fetch(`/finance/customer/account/json/${customerId}/`, {
        method: "POST",
        headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"), 
        },
        body: JSON.stringify(data),
    })
    .then(response => response.json())
    .then(data => {
        const balanceEl = document.querySelector('#due_balance')
        balanceEl.innerHTML=''

        const previousDueEl = document.querySelector('#previous_due');
        console.log(currencyData[0], currencyData)
        const balance = data.find(item => item.currency__symbol === currencyData[0][0]?.symbol);
       
        if (balance) {
          previousDueEl.textContent = `${balance.currency__symbol} ${balance.balance}`;
        } else {
          previousDueEl.textContent = "0.00" 
        }
        
        
        data.forEach((balance)=>{
            balanceEl.innerHTML +=`<small id='id_due' class='text-danger'>${balance?.currency__symbol} ${balance?.balance}</small>`
        })
    })
    .catch((error) => {
    console.error("Error:", error);
});
}

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