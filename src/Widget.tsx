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

  // Fonction pour basculer l'état plié/déplié et ajuster la position
  const toggleExpand = () => {
    const shouldExpand = !isExpanded;
    setIsExpanded(shouldExpand);

    // Si on déplie le widget
    if (shouldExpand && widgetRef.current) {
      // Utiliser setTimeout pour laisser le temps au DOM de se mettre à jour
      // et au widget d'obtenir sa nouvelle hauteur 'auto' (ou maxHeight)
      setTimeout(() => {
        if (widgetRef.current) {
          const widgetRect = widgetRef.current.getBoundingClientRect();
          const widgetWidth = widgetRect.width;
          const widgetHeight = widgetRect.height; // Utiliser getBoundingClientRect qui est plus fiable que offsetHeight après des changements CSS complexes
          const windowWidth = window.innerWidth;
          const windowHeight = window.innerHeight;
          const currentX = position.x;
          const currentY = position.y;
          const margin = 20; // Marge commune pour droite et bas

          // Log temporaire pour débogage
          console.log('[Widget] toggleExpand Adjust Check:', {
              currentX, currentY, widgetWidth, widgetHeight, windowWidth, windowHeight
          });

          let newX = currentX;
          let newY = currentY;

          // Ajustement X (gauche)
          const rightEdge = currentX + widgetWidth;
          const rightLimit = windowWidth - margin;
          if (rightEdge > rightLimit) {
            // Calcul: Positionner le bord droit du widget à `rightLimit`
            newX = rightLimit - widgetWidth; // Equivalent à windowWidth - margin - widgetWidth
            console.log(`[Widget] Adjusting X: rightEdge (${rightEdge.toFixed(0)}) > rightLimit (${rightLimit.toFixed(0)}). New X calculated: ${newX.toFixed(0)}`);
          }
          // Empêcher de déborder à gauche
          newX = Math.max(margin, newX);

          // Ajustement Y (haut)
          const bottomEdge = currentY + widgetHeight;
          const bottomLimit = windowHeight - margin;
          if (bottomEdge > bottomLimit) {
             // Calcul: Positionner le bord bas du widget à `bottomLimit`
            newY = bottomLimit - widgetHeight; // Equivalent à windowHeight - margin - widgetHeight
             console.log(`[Widget] Adjusting Y: bottomEdge (${bottomEdge.toFixed(0)}) > bottomLimit (${bottomLimit.toFixed(0)}). New Y calculated: ${newY.toFixed(0)}`);
          }
          // Empêcher de déborder en haut
          newY = Math.max(margin, newY);

          // Mettre à jour la position seulement si elle a changé
          if (newX !== currentX || newY !== currentY) {
             console.log(`[Widget] Updating position from (${currentX.toFixed(0)}, ${currentY.toFixed(0)}) to (${newX.toFixed(0)}, ${newY.toFixed(0)})`);
             setPosition({ x: newX, y: newY });
          } else {
              console.log('[Widget] No position update needed.');
          }
        }
      }, 100); // <-- Délai augmenté à 100ms
    }
  };

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
      const target = e.target as HTMLElement;

      // Ne jamais démarrer le drag si la cible est un élément interactif ou à l'intérieur d'un élément interactif
      if (target.closest('input, select, button, textarea')) {
          return; // Laisse l'événement par défaut (focus, clic, etc.) se produire
      }

      // Si le widget est plié, ne pas démarrer le drag (le seul clic géré est sur le bouton central pour déplier)
      if (!isExpanded) {
          return;
      }

      // Si on arrive ici, le widget est déplié ET on n'a pas cliqué sur un contrôle.
      // On peut donc démarrer le drag.
      const coords = getEventCoordinates(e);
      if (widgetRef.current && coords) {
          const rect = widgetRef.current.getBoundingClientRect();
          setDragStartOffset({
              x: coords.x - rect.left,
              y: coords.y - rect.top
          });
          setIsDragging(true);
          // PAS de e.preventDefault() ici. Le preventDefault dans handleDragMove
          // suffira pour empêcher le scroll PENDANT le drag actif.
      }
  }, [isExpanded]); // dragStartOffset n'est pas nécessaire en dépendance

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
    cursor: isExpanded ? (isDragging ? 'grabbing' : 'grab') : 'pointer',
    userSelect: isDragging ? 'none' : 'auto', // Empêcher la sélection SEULEMENT pendant le drag
    zIndex: 9999,
    borderRadius: isExpanded ? '8px' : '50%', // Rond si plié
    boxShadow: '0 4px 12px rgba(0,0,0,0.15)', // Ombre portée
    transition: 'width 0.3s ease, height 0.3s ease, border-radius 0.3s ease', 
    backgroundColor: 'white', // Fond blanc par défaut
    display: 'flex', // Utiliser flex pour la structure interne
    flexDirection: 'column', // Empiler header et content
    // Revenir à 'hidden' pour le conteneur global pour éviter les problèmes de performance/layout
    // Les scrollbars internes (ex: réponse) gèreront le dépassement de leur propre contenu.
    overflow: 'hidden', 
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
            style={{ cursor: 'default', padding: '10px', borderBottom: '1px solid #eee', backgroundColor: '#f8f8f8', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }} 
          >
            <span>Chatbot LivrerJardiner</span>
            {/* Bouton pour réduire */}
            <button 
              onClick={toggleExpand} 
              title="Réduire"
              style={{
                background: 'none',
                border: 'none',
                color: '#555',
                fontSize: '18px',
                cursor: 'pointer',
                padding: '0 5px',
                lineHeight: '1'
              }}
            >
              _
            </button>
          </div>
          <div className="widget-content" style={{ padding: '10px', overflowY: 'auto', flexGrow: 1 /* Permet au contenu de prendre l'espace et de scroller */ }}>
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