// src/Widget.tsx
import React, { useState, useRef, useEffect, useCallback } from 'react';
import './Widget.css';
// Importer une icône (optionnel, vous pouvez utiliser du texte ou un emoji)
// import { ChatBubbleOvalLeftEllipsisIcon } from '@heroicons/react/24/solid'; 

const Widget: React.FC = () => {
  const [input, setInput] = useState<string>('');
  const [response, setResponse] = useState<string>('');
  const [userEmail, setUserEmail] = useState<string>('');
  const [deliveryMethod, setDeliveryMethod] = useState<string>('livraison');
  const [selectedModel, setSelectedModel] = useState<string>('mistral');
  const [position, setPosition] = useState<{ x: number; y: number }>({ x: window.innerWidth - 80, y: window.innerHeight - 80 }); // Position initiale en bas à droite
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStartOffset, setDragStartOffset] = useState<{ x: number, y: number }>({ x: 0, y: 0 });
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isOrdering, setIsOrdering] = useState<boolean>(false);
  const [showOrderButton, setShowOrderButton] = useState<boolean>(false);
  const [canPlaceOrder, setCanPlaceOrder] = useState<boolean>(false);
  const [orderableItem, setOrderableItem] = useState<string | null>(null);
  const [orderableQuantity, setOrderableQuantity] = useState<number>(0);
  const [isExpanded, setIsExpanded] = useState<boolean>(false); // <-- Nouvel état pour plié/déplié, commence plié
  const widgetRef = useRef<HTMLDivElement>(null);

  const toggleExpand = () => setIsExpanded(!isExpanded);

  // Fonction helper pour obtenir les coordonnées (souris ou tactile)
  const getEventCoordinates = (e: React.MouseEvent | MouseEvent | React.TouchEvent | TouchEvent): { x: number; y: number } | null => {
      if ('touches' in e) {
          // Touch event
          if (e.touches.length > 0) {
              return { x: e.touches[0].clientX, y: e.touches[0].clientY };
          }
      } else {
          // Mouse event
          return { x: e.clientX, y: e.clientY };
      }
      return null; // Si pas de coordonnées (ex: touchend sans touches)
  }

  // Gestionnaire de début de drag (commun pour souris et tactile)
  const handleDragStart = useCallback((e: React.MouseEvent | React.TouchEvent) => {
      // Ne pas démarrer le drag si:
      // 1. Widget plié
      // 2. Clic/touch sur un élément interactif (input, select, button)
      // 3. Clic/touch sur l'en-tête (pour permettre le pliage/dépliage)
      const target = e.target as Node;
      if (!isExpanded || 
          (target instanceof HTMLInputElement) || 
          (target instanceof HTMLSelectElement) || 
          (target instanceof HTMLButtonElement)) {
          const header = widgetRef.current?.querySelector('.widget-header');
          if (header && header.contains(target)) {
              return; // Ne pas démarrer le drag si on clique sur le header
          }
          if (!isExpanded) return; // Double sécurité: si pas déplié, on sort
      }

      const coords = getEventCoordinates(e);
      if (widgetRef.current && coords) {
          const rect = widgetRef.current.getBoundingClientRect();
          setDragStartOffset({
              x: coords.x - rect.left,
              y: coords.y - rect.top
          });
          setIsDragging(true);
          // Prévenir sélection texte pour souris, comportement par défaut pour toucher (scroll) sera géré dans handleDragMove
          if (!('touches' in e)) {
              e.preventDefault(); 
          }
      }
  }, [isExpanded]);

  // Gestionnaire de mouvement (commun)
  const handleDragMove = useCallback((e: MouseEvent | TouchEvent) => {
    if (!isDragging) return;

    const coords = getEventCoordinates(e);
    if (coords) {
        const newX = coords.x - dragStartOffset.x;
        const newY = coords.y - dragStartOffset.y;
        setPosition({ x: newX, y: newY });
    }
    
    // Empêche le défilement de la page pendant le drag tactile
    if ('touches' in e) {
        e.preventDefault();
    }

  }, [isDragging, dragStartOffset]);

  // Gestionnaire de fin de drag (commun)
  const handleDragEnd = useCallback(() => {
    if (isDragging) {
      setIsDragging(false);
    }
  }, [isDragging]);

  // Effet pour ajouter/supprimer les listeners globaux (move/end) lors du drag
  useEffect(() => {
    if (isDragging) {
      // Utiliser { passive: false } pour touchmove pour pouvoir appeler preventDefault()
      window.addEventListener('mousemove', handleDragMove);
      window.addEventListener('touchmove', handleDragMove, { passive: false });
      window.addEventListener('mouseup', handleDragEnd);
      window.addEventListener('touchend', handleDragEnd);
      window.addEventListener('mouseleave', handleDragEnd); // Sécurité si souris sort
    }
    return () => {
      window.removeEventListener('mousemove', handleDragMove);
      window.removeEventListener('touchmove', handleDragMove);
      window.removeEventListener('mouseup', handleDragEnd);
      window.removeEventListener('touchend', handleDragEnd);
      window.removeEventListener('mouseleave', handleDragEnd);
    };
  }, [isDragging, handleDragMove, handleDragEnd]);

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
      params.append('selected_model', selectedModel);

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

  // Ajuster les styles dynamiquement
  const containerStyle: React.CSSProperties = {
    position: 'fixed',
    left: `${position.x}px`,
    top: `${position.y}px`,
    width: isExpanded ? '300px' : '60px', // Taille différente si plié/déplié
    height: isExpanded ? 'auto' : '60px',
    maxHeight: isExpanded ? '600px': '60px', // Limite hauteur déplié
    cursor: isExpanded ? (isDragging ? 'grabbing' : 'grab') : 'pointer', // Curseur différent si plié
    userSelect: 'none',
    zIndex: 9999,
    borderRadius: isExpanded ? '8px' : '50%', // Rond si plié
    overflow: 'hidden', // Cache le contenu si plié et plus petit
    boxShadow: '0 4px 12px rgba(0,0,0,0.15)', // Ombre portée
    transition: 'width 0.3s ease, height 0.3s ease, border-radius 0.3s ease', // Animation douce
    backgroundColor: 'white', // Fond blanc par défaut
  };

  const collapsedButtonStyle: React.CSSProperties = {
      width: '100%',
      height: '100%',
      border: 'none',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', // Dégradé exemple
      color: 'white',
      borderRadius: '50%',
      fontSize: '28px', // Taille de l'emoji/icône
      cursor: 'pointer',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      outline: 'none',
      boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
  };


  return (
    <div
      ref={widgetRef}
      className={`widget-container ${isExpanded ? 'expanded' : 'collapsed'}`}
      style={containerStyle}
      onMouseDown={handleDragStart} // Utilise le gestionnaire commun
      onTouchStart={handleDragStart} // Utilise le gestionnaire commun
    >
      {isExpanded ? (
        <>
          {/* Widget Déplié */}
          <div
            className="widget-header"
            onClick={toggleExpand} // Toujours pour replier
            style={{ cursor: 'pointer', padding: '10px', borderBottom: '1px solid #eee', backgroundColor: '#f8f8f8' }} 
          >
            Chatbot LivrerJardiner <span style={{ float: 'right', fontWeight: 'bold' }}>_</span>
          </div>
          <div className="widget-content" style={{ padding: '10px' }}>
            {/* Input texte */}
            <input
              type="text"
              className="widget-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ex. : Je veux 10 rosiers"
            />

            {/* Sélecteur de Modèle */}
            <select
              className="widget-input widget-select model-selector"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              disabled={isLoading || isOrdering}
              style={{ marginTop: '5px' }}
            >
              <option value="mistral">Modèle Rapide (Mistral)</option>
              <option value="llama3">Modèle Avancé (Meta)</option>
            </select>

            {/* Bouton Envoyer */}
            <button
              onClick={sendRequest}
              className="widget-button widget-button-send"
              disabled={isLoading || isOrdering}
              style={{ marginTop: '5px' }}
            >
              {isLoading ? 'Chargement...' : 'Posez votre question...'}
            </button>

            {/* Zone de réponse */}
            <div
              className={`widget-response-area ${(isLoading || isOrdering) ? 'is-loading' : ''}`}
              style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: (isLoading || isOrdering) ? 'center' : 'flex-start',
                minHeight: '100px', 
                maxHeight: '200px', 
                overflowY: 'auto', 
                marginTop: '10px',
                border: '1px solid #eee',
                borderRadius: '4px',
                padding: '8px',
                backgroundColor: '#f9f9f9',
                wordBreak: 'break-word',
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

            {/* Section Commande */}
            {showOrderButton && (
              <div style={{ marginTop: '10px', borderTop: '1px solid #eee', paddingTop: '10px' }}>
                <input
                  type="email"
                  className="widget-input"
                  value={userEmail}
                  onChange={(e) => setUserEmail(e.target.value)}
                  placeholder="Votre email *"
                  required
                />
                <select
                  className="widget-input widget-select"
                  value={deliveryMethod}
                  onChange={(e) => setDeliveryMethod(e.target.value)}
                  style={{ marginTop: '5px' }}
                >
                  <option value="livraison">Mode : Livraison</option>
                  <option value="retrait">Mode : Retrait</option>
                </select>

                <button
                  onClick={handleOrderClick}
                  className="widget-button widget-button-order"
                  disabled={isOrdering || isLoading}
                  style={{ marginTop: '5px' }}
                >
                  {isOrdering ? 'Envoi...' : 'Commander'}
                </button>
              </div>
            )}
          </div>
        </>
      ) : (
        <>
          {/* Widget Plié (Bouton) */}
          <button
             onClick={toggleExpand} // Pour déplier
             style={collapsedButtonStyle}
             title="Ouvrir le chat"
           >
             💬 
           </button>
        </>
      )}
    </div>
  );
};

export default Widget;