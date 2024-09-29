import React, { useState } from "react";
import './App.css';

function App() {
  const [order, setOrder] = useState("");
  const [pickup, setPickup] = useState(false);
  const [delivery, setDelivery] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (order && (pickup || delivery)) {
      const output = {
        order: order,
        delivery: delivery
      };
      console.log(output);
      alert(`Order submitted: ${JSON.stringify(output)}`);
    } else {
      alert("Please enter your order and select a delivery option.");
    }
  };

  return (
    <>
      <header>
        <h1>Food Delight - Online Ordering</h1>
      </header>
      <div className="hero">
        <h1>Welcome to Food Delight</h1>
      </div>
      <div className="container">
        <h2>Place Your Order</h2>
        <form onSubmit={handleSubmit} className="order-form">
          <textarea
            placeholder="Enter your order..."
            value={order}
            onChange={(e) => setOrder(e.target.value)}
            rows="4"
          />
          <div className="delivery-options">
            <label className="checkbox-container">
              <input 
                type="checkbox" 
                checked={pickup} 
                onChange={() => setPickup(!pickup)} 
              />
              Pick Up
              <span className="checkmark"></span>
            </label>
            <label className="checkbox-container">
              <input 
                type="checkbox" 
                checked={delivery} 
                onChange={() => setDelivery(!delivery)} 
              />
              Delivery
              <span className="checkmark"></span>
            </label>
          </div>
          <button type="submit" className="submit-btn">
            Submit Order
          </button>
        </form>
      </div>
      <footer>
        <p>Powered by Imagination & Modern Web © 2024</p>
      </footer>
    </>
  );
}

export default App;
