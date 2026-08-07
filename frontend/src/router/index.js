import { createRouter, createWebHistory } from 'vue-router'
import ProductList from '../views/ProductList.vue'
import CartView from '../views/CartView.vue'
import CheckoutView from '../views/CheckoutView.vue'
import AgentDemo from '../views/AgentDemo.vue'
import AccountView from '../views/AccountView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: ProductList },
    { path: '/cart', component: CartView },
    { path: '/checkout', component: CheckoutView },
    { path: '/agent', component: AgentDemo },
    { path: '/account', component: AccountView },
  ],
})
