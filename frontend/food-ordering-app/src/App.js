import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Route, Routes, Link, useNavigate } from "react-router-dom";
import './App.css';

function Navigation() {
  return (
    <nav>
      <ul>
        <li><Link to="/">Home</Link></li>
        <li><Link to="/health">Health Check</Link></li>
      </ul>
    </nav>
  );
}

function HealthCheck() {
  const [status, setStatus] = useState("Checking...");
  const navigate = useNavigate();

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await new Promise(resolve => setTimeout(resolve)); // Simulate network delay
        setStatus("OK");
        console.log("Health Check: HTTP 200 OK");
      } catch (error) {
        setStatus("Error");
        console.error("Health check failed:", error);
      }
    };

    checkHealth();
  }, [navigate]);

  return (
    <div>
      <h2>Health Check</h2>
      <p>Status: {status}</p>
      <p>Version: 1.0.0</p>
      <p>Timestamp: {new Date().toISOString()}</p>
    </div>
  );
}

function OrderForm() {
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
  );
}

function App() {
  return (
    <Router>
      <header>
        <h1>Food Delight - Online Ordering</h1>
        <Navigation />
      </header>
      <div className="hero">
        <h1>Welcome to Food Delight</h1>
      </div>
      <Routes>
        <Route path="/health" element={<HealthCheck />} />
        <Route path="/" element={<OrderForm />} />
      </Routes>
      <footer>
        <p>Powered by Imagination & Modern Web © 2024</p>
      </footer>
    </Router>
  );
}

export default App;