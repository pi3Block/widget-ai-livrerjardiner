// src/Widget.tsx
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createRoot } from 'react-dom/client';

const Widget: React.FC = () => {
  const [input, setInput] = useState<string>('');
  const [response, setResponse] = useState<string>('');
  const [position, setPosition] = useState<{ x: number; y: number }>({ x: 100, y: 100 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStartOffset, setDragStartOffset] = useState<{ x: number, y: number }>({ x: 0, y: 0 });
  const widgetRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (widgetRef.current) {
      const rect = widgetRef.current.getBoundingClientRect();
      setDragStartOffset({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      });
      setIsDragging(true);
      e.preventDefault();
    }
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging) return;
    const newX = e.clientX - dragStartOffset.x;
    const newY = e.clientY - dragStartOffset.y;
    setPosition({ x: newX, y: newY });
  }, [isDragging, dragStartOffset]);

  const handleMouseUp = useCallback(() => {
    if (isDragging) {
      setIsDragging(false);
    }
  }, [isDragging]);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      window.addEventListener('mouseleave', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('mouseleave', handleMouseUp);
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  const sendRequest = async () => {
    try {
      const url = `https://api.livrerjardiner.fr/chat?input=${encodeURIComponent(input)}`;
      console.log('Envoi de la requête à :', url);
      const res = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error(`Erreur HTTP : ${res.status} ${res.statusText}`);
      const data = await res.json();
      console.log('Réponse reçue :', data);
      setResponse(data.message || 'Réponse invalide ou vide.');
    } catch (error) {
      console.error('Erreur lors de la requête API:', error);
      if (error instanceof Error) {
        setResponse(`Erreur de communication : ${error.message}`);
      } else {
        setResponse('Erreur de communication inconnue.');
      }
    }
  };

  return (
    <div
      ref={widgetRef}
      style={{
        position: 'fixed',
        left: `${position.x}px`,
        top: `${position.y}px`,
        width: '300px',
        padding: '0',
        backgroundColor: '#f0f0f0',
        border: '1px solid #ccc',
        borderRadius: '5px',
        cursor: isDragging ? 'grabbing' : 'grab',
        userSelect: 'none',
        zIndex: 9999,
        boxShadow: '0 4px 8px rgba(0,0,0,0.1)',
        display: 'flex',
        flexDirection: 'column',
      }}
      onMouseDown={handleMouseDown}
    >
      <div style={{ padding: '8px 10px', backgroundColor: '#ddd', textAlign: 'center', cursor: 'move', borderTopLeftRadius: '5px', borderTopRightRadius: '5px' }}>
        Chatbot LivrerJardiner
      </div>
      <div style={{ padding: '10px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ex. : Je veux 10 rosiers"
          onMouseDown={(e) => e.stopPropagation()}
          style={{ padding: '10px', boxSizing: 'border-box', border: '1px solid #ccc', borderRadius: '3px' }}
        />
        <button
          onClick={sendRequest}
          onMouseDown={(e) => e.stopPropagation()}
          style={{ padding: '10px', boxSizing: 'border-box', cursor: 'pointer', border: 'none', backgroundColor: '#007bff', color: 'white', borderRadius: '3px' }}
        >
          Envoyer
        </button>
        <div
          onMouseDown={(e) => e.stopPropagation()}
          style={{
            wordWrap: 'break-word',
            minHeight: '40px',
            maxHeight: '150px',
            overflowY: 'auto',
            backgroundColor: '#e9e9e9',
            padding: '8px',
            border: '1px solid #d0d0d0',
            borderRadius: '4px',
            fontSize: '0.9em',
            lineHeight: '1.4',
          }}
        >
          {response || 'Posez votre question...'}
        </div>
      </div>
    </div>
  );
};

export default Widget;