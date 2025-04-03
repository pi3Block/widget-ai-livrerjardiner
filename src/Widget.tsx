// src/Widget.tsx
import React, { useState, useRef, useEffect, useCallback } from 'react';
import './Widget.css';

const Widget: React.FC = () => {
  const [input, setInput] = useState<string>('');
  const [response, setResponse] = useState<string>('');
  const [userEmail, setUserEmail] = useState<string>('');
  const [deliveryMethod, setDeliveryMethod] = useState<string>('livraison');
  const [position, setPosition] = useState<{ x: number; y: number }>({ x: 100, y: 100 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStartOffset, setDragStartOffset] = useState<{ x: number, y: number }>({ x: 0, y: 0 });
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [showOrderButton, setShowOrderButton] = useState<boolean>(false);
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
    if (!userEmail) {
      setResponse("Veuillez entrer votre email pour continuer.");
      return;
    }
    if (!/\S+@\S+\.\S+/.test(userEmail)) {
      setResponse("Veuillez entrer un format d'email valide.");
      return;
    }

    setIsLoading(true);
    setResponse('');
    setShowOrderButton(false);
    try {
      const url = `https://api.livrerjardiner.fr/chat?input=${encodeURIComponent(input)}&user_email=${encodeURIComponent(userEmail)}&delivery_method=${encodeURIComponent(deliveryMethod)}`;
      console.log('Envoi de la requête à :', url);
      const res = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error(`Erreur HTTP : ${res.status} ${res.statusText}`);
      const data = await res.json();
      console.log('Réponse reçue :', data);
      const message = data.message || 'Réponse invalide ou vide.';
      setResponse(message);

      if (message.toLowerCase().includes('rosiers')) {
        setShowOrderButton(true);
      }

    } catch (error) {
      console.error('Erreur lors de la requête API:', error);
      if (error instanceof Error) {
        setResponse(`Erreur de communication : ${error.message}`);
      } else {
        setResponse('Erreur de communication inconnue.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleOrderClick = () => {
    console.log('Clic sur Commander !');
    alert('Commande en cours de développement !');
    setShowOrderButton(false);
  };

  return (
    <div
      ref={widgetRef}
      className="widget-container"
      style={{
        position: 'fixed',
        left: `${position.x}px`,
        top: `${position.y}px`,
        width: '300px',
        cursor: isDragging ? 'grabbing' : 'grab',
        userSelect: 'none',
        zIndex: 9999,
      }}
      onMouseDown={handleMouseDown}
    >
      <div className="widget-header">
        Chatbot LivrerJardiner
      </div>
      <div className="widget-content">
        <input
          type="text"
          className="widget-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ex. : Je veux 10 rosiers"
          onMouseDown={(e) => e.stopPropagation()}
        />
        <input
          type="email"
          className="widget-input"
          value={userEmail}
          onChange={(e) => setUserEmail(e.target.value)}
          placeholder="Votre email *"
          required
          onMouseDown={(e) => e.stopPropagation()}
        />
        <select
          className="widget-input widget-select"
          value={deliveryMethod}
          onChange={(e) => setDeliveryMethod(e.target.value)}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <option value="livraison">Mode : Livraison</option>
          <option value="retrait">Mode : Retrait</option>
        </select>
        <button
          onClick={sendRequest}
          className="widget-button widget-button-send"
          onMouseDown={(e) => e.stopPropagation()}
        >
          Envoyer
        </button>
        <div
          className={`widget-response-area ${isLoading ? 'is-loading' : ''}`}
          onMouseDown={(e) => e.stopPropagation()}
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: isLoading ? 'center' : 'flex-start',
            minHeight: '60px',
            maxHeight: '180px',
          }}
        >
          {isLoading ? (
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          ) : (
            <span className="response-content">
              {response || 'Posez votre question...'}
            </span>
          )}
        </div>

        {showOrderButton && (
          <button
            onClick={handleOrderClick}
            className="widget-button widget-button-order"
            onMouseDown={(e) => e.stopPropagation()}
          >
            Commander
          </button>
        )}
      </div>
    </div>
  );
};

export default Widget;