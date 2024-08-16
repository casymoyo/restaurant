// product validation js
const submitButton = document.querySelector('#id_submit')
//price validation
document.querySelector('#id_price').addEventListener(
    'input', ()=>{
        const cost = Number(document.querySelector('#id_cost')?.value)
        const price = Number(document.querySelector('#id_price')?.value)
        const errorElement = document.querySelector('#price_error')

        if (price<=0){
            errorElement.innerHTML='*selling price cant be zero'
            submitButton.disabled = true
        }else if(price<cost){
            errorElement.innerHTML='*selling price cant be less than cost price'
            submitButton.disabled = true
        }else{
            errorElement.innerHTML=''
            submitButton.disabled = false
        }
    }
)
// cost validation
document.querySelector('#id_cost')?.addEventListener(
    'input', ()=>{
        const cost = Number(document.querySelector('#id_cost')?.value)
        const errorElement = document.querySelector('#cost_error')
        
        if (cost<=0){
            errorElement.innerHTML='*cost cant be zero'
            submitButton.disabled = true
        }else{
            errorElement.innerHTML=''
            submitButton.disabled = false
        }
    }
)
// quantity validation
document.querySelector('#id_quantity').addEventListener(
    'input', ()=>{
        const quantity = Number(document.querySelector('#id_quantity')?.value)
        const errorElement = document.querySelector('#quantity_error')

        if (quantity<=0){
            errorElement.innerHTML='*quantity cant be zero'
            submitButton.disabled = true
        }else{
            errorElement.innerHTML=''
            submitButton.disabled = false
        }
    }
)