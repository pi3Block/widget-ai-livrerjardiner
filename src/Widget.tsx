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
  const [isOrdering, setIsOrdering] = useState<boolean>(false);
  const [showOrderButton, setShowOrderButton] = useState<boolean>(false);
  const [canPlaceOrder, setCanPlaceOrder] = useState<boolean>(false);
  const [orderableItem, setOrderableItem] = useState<string | null>(null);
  const [orderableQuantity, setOrderableQuantity] = useState<number>(0);
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
    setIsLoading(true);
    setResponse('');
    setShowOrderButton(false);
    setCanPlaceOrder(false);
    setOrderableItem(null);
    setOrderableQuantity(0);

    try {
      const params = new URLSearchParams();
      params.append('input', input);
      params.append('delivery_method', deliveryMethod);

      const baseUrl = 'https://api.livrerjardiner.fr/chat';
      const url = `${baseUrl}?${params.toString()}`;

      console.log('Envoi de la requête /chat à :', url);
      const res = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!res.ok) {
          const errorData = await res.json().catch(() => ({ message: `Erreur HTTP : ${res.status} ${res.statusText}` }));
          throw new Error(errorData.message || `Erreur HTTP : ${res.status} ${res.statusText}`);
      }

      const data = await res.json();
      console.log('Réponse /chat reçue :', data);

      setResponse(data.message || 'Réponse invalide ou vide.');
      setCanPlaceOrder(data.can_order || false);
      setOrderableItem(data.item || null);
      setOrderableQuantity(data.quantity || 0);

      if (data.can_order) {
        setShowOrderButton(true);
      }

    } catch (error) {
      console.error('Erreur lors de la requête /chat API:', error);
      if (error instanceof Error) {
        setResponse(`Erreur de communication : ${error.message}`);
      } else {
        setResponse('Erreur de communication inconnue.');
      }
      setShowOrderButton(false);
      setCanPlaceOrder(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOrderClick = async () => {
    if (!userEmail) {
      setResponse("Veuillez entrer votre email avant de commander.");
      return;
    }
    if (!/\S+@\S+\.\S+/.test(userEmail)) {
      setResponse("Format d'email invalide. Veuillez corriger avant de commander.");
      return;
    }

    if (!orderableItem || orderableQuantity <= 0) {
        setResponse("Impossible de passer la commande, détails manquants. Veuillez reposer votre question.");
        return;
    }

    setIsOrdering(true);
    setResponse('');

    try {
        const orderData = {
            user_email: userEmail,
            item: orderableItem,
            quantity: orderableQuantity,
            delivery_method: deliveryMethod,
        };

        const orderUrl = 'https://api.livrerjardiner.fr/order';
        console.log('Envoi de la requête /order à :', orderUrl, 'avec data:', orderData);

        const res = await fetch(orderUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(orderData),
        });

        const resultData = await res.json();

        if (!res.ok) {
            console.error('Erreur réponse /order:', resultData);
            throw new Error(resultData.detail || resultData.message || `Erreur lors de la commande: ${res.status}`);
        }

        console.log('Réponse /order reçue :', resultData);
        setResponse(resultData.message || 'Commande traitée avec succès !');
        setShowOrderButton(false);
        setCanPlaceOrder(false);

    } catch (error) {
        console.error('Erreur lors de la requête /order API:', error);
        if (error instanceof Error) {
            setResponse(`Erreur lors de la commande : ${error.message}`);
        } else {
            setResponse('Erreur inconnue lors de la commande.');
        }
    } finally {
        setIsOrdering(false);
    }
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
          disabled={isLoading || isOrdering}
          onMouseDown={(e) => e.stopPropagation()}
        >
          {isLoading ? 'Chargement...' : 'Envoyer'}
        </button>
        <div
          className={`widget-response-area ${(isLoading || isOrdering) ? 'is-loading' : ''}`}
          onMouseDown={(e) => e.stopPropagation()}
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: (isLoading || isOrdering) ? 'center' : 'flex-start',
            minHeight: '60px',
            maxHeight: '180px',
          }}
        >
          {(isLoading || isOrdering) ? (
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
            disabled={isOrdering || isLoading}
            onMouseDown={(e) => e.stopPropagation()}
          >
            {isOrdering ? 'Envoi...' : 'Commander'}
          </button>
        )}
      </div>
    </div>
  );
};

export default Widget;