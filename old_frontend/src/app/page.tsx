'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';
import Menu from '@/components/Menu'; // Adjusted import path

const API_BASE_URL = 'http://localhost:5001'; // Backend URL
const POLLING_INTERVAL = 500; // Poll every 0.5 seconds

export default function Home() {
  const [mode, setMode] = useState<'standby' | 'menu' | 'loading'>('loading');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMode = async () => {
      try {
        const response = await axios.get<{ mode: 'standby' | 'menu' }>(`${API_BASE_URL}/mode`);
        setMode(response.data.mode);
        setError(null); // Clear error on successful fetch
      } catch (err) {
        console.error("Error fetching mode:", err);
        setError("Could not connect to backend to fetch mode.");
        // Keep the last known mode or switch to standby?
        // setMode('standby'); // Optional: default to standby on error
      }
    };

    // Fetch immediately on mount
    fetchMode();

    // Set up polling interval
    const intervalId = setInterval(fetchMode, POLLING_INTERVAL);

    // Clean up interval on component unmount
    return () => clearInterval(intervalId);
  }, []); // Empty dependency array means this effect runs once on mount and cleans up on unmount

  // Render based on mode
  if (mode === 'loading') {
    return <div className="min-h-screen bg-black text-white flex items-center justify-center">Connecting...</div>;
  }
  
  if (error) {
     return <div className="min-h-screen bg-black text-red-500 flex items-center justify-center p-4 text-center">Error: {error}</div>;
  }

  if (mode === 'menu') {
    return <Menu />;
  }

  // Default: standby mode (blank screen)
  return <div className="min-h-screen bg-black"></div>; 
}
