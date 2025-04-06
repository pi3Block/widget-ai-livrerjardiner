import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig(({ command, mode }) => {
  // Charger les variables d'environnement spécifiques au mode
  const env = loadEnv(mode, process.cwd(), '');

  // Configuration de base partagée
  const baseConfig = {
    plugins: [react()],
  };

  // Configuration spécifique pour le build du WIDGET
  if (env.VITE_BUILD_TARGET === 'widget') {
    return {
      ...baseConfig,
      build: {
        lib: {
          entry: path.resolve(__dirname, 'src/widget-entry.tsx'), // Assurez-vous que ce chemin est correct
          name: 'LivrerJardinerWidget', // Nom de la variable globale si UMD/IIFE
          formats: ['umd', 'es'], // UMD pour <script>, ES pour import
          fileName: (format) => `livrerjardiner-widget.${format}.js` // Le nom de fichier souhaité
        },
        rollupOptions: {
          // Externaliser React/ReactDOM pour ne pas les inclure dans le bundle widget
          // L'environnement hôte devra les fournir
          external: ['react', 'react-dom'],
          output: {
            globals: {
              react: 'React',
              'react-dom': 'ReactDOM'
            }
          }
        },
        outDir: 'dist/widget', // Sortie dans un sous-dossier dédié
        emptyOutDir: true, // Nettoyer le dossier avant build
      }
    };
  }

  // Configuration par défaut pour le build de l'ADMIN (ou dev)
  return {
    ...baseConfig,
    // 'base' nécessaire si l'admin n'est pas servi depuis la racine du domaine
    // base: '/', 
    build: {
      rollupOptions: {
        input: {
          // Point d'entrée de l'admin SPA utilisant index.html
          admin: path.resolve(__dirname, 'index.html') 
        },
        output: {
          entryFileNames: `assets/[name].[hash].js`,
          chunkFileNames: `assets/[name].[hash].js`,
          assetFileNames: `assets/[name].[hash].[ext]`
        }
      },
      outDir: 'dist/admin', // Sortie dans un sous-dossier dédié
      emptyOutDir: true, // Nettoyer le dossier avant build
    }
  };
});
