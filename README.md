# restaurant
Restaurant MVP
 <!-- document.addEventListener('DOMContentLoaded', function () {
            fetchMealsAndDrinks();
            document.getElementById('food').addEventListener('click', () => showCategory('Food'));
            document.getElementById('drinks').addEventListener('click', () => showCategory('Drinks'));
            document.getElementById('food_search').addEventListener('input', searchItems);
        });

        function fetchMealsAndDrinks() {
            fetch('{% url "pos:product_meal_json" %}')
                .then(response => response.json())
                .then(data => {
                    console.log(data)
                    meals = data.meals;
                    drinks = data.products;
                    renderItems(meals, 'Food');
                    renderItems(drinks, 'Drinks');
                    showCategory('Food'); 
                    
                })
                .catch(error => console.error('Error fetching data:', error));
        }

        function renderItems(items, category) {
            console.log('hre')
            const container = document.getElementById(category);
            container.innerHTML = '';
            items.forEach(item => {
                const itemCard = `
                    <div class="col-md-3 mt-3" onclick="addToCart(${item.id}, '${item.name}', ${item.price})">
                        <div class="card mb-4 hover box-shadow" style="border: none;">
                            <div class="card-body">
                                <p class="card-text text-center">${item.name} $${item.price}</p>
                            </div>
                        </div>
                    </div>
                `;
                container.innerHTML += itemCard;
            });
        }

        function showCategory(category) {
            document.getElementById('Food').style.display = category === 'Food' ? 'block' : 'none';
            document.getElementById('Drinks').style.display = category === 'Drinks' ? 'block' : 'none';
        }

        function searchItems() {
            const query = document.getElementById('food_search').value.toLowerCase();
            const filteredMeals = meals.filter(meal => meal.name.toLowerCase().includes(query));
            const filteredDrinks = drinks.filter(drink => drink.name.toLowerCase().includes(query));

            if (document.getElementById('Food').style.display === 'block') {
                renderItems(filteredMeals, 'Food');
            } else {
                renderItems(filteredDrinks, 'Drinks');
            }
        } -->
