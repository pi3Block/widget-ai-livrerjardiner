import React from 'react';
// Importer les composants nécessaires de react-admin
import { 
    List, 
    Datagrid, 
    TextField, 
    NumberField, 
    ReferenceField, // Pour afficher la catégorie liée
    FunctionField,   // Pour calculer/afficher le nombre de variations
    Edit, 
    SimpleForm, 
    TextInput, 
    NumberInput,
    ReferenceInput, // Pour sélectionner la catégorie
    SelectInput,    // Input pour ReferenceInput
    ArrayField, 
    Datagrid as SimpleDatagrid, // Renommer pour éviter conflit
    Create // Importer Create
} from 'react-admin';
import type { Product } from '../types'; // Ajustement potentiel du chemin si types est partagé

/**
 * Composant pour afficher la liste des produits.
 */
export const ProductList = () => (
  <List>
    <Datagrid rowClick="edit"> 
      <TextField source="id" /> 
      <TextField source="name" label="Nom du Produit" /> 
      <TextField source="base_description" label="Description" /> 

      {/* Afficher le nom de la catégorie via ReferenceField */}
      <ReferenceField source="category_id" reference="categories" link={false} label="Catégorie">
         {/* link={false} pour ne pas rendre le nom cliquable vers la catégorie */} 
         {/* Utilise les données chargées depuis la ressource 'categories' */} 
         <TextField source="name" /> 
      </ReferenceField>

      {/* Afficher le nombre de variations */}
      <FunctionField
          label="Variations"
          render={(record?: Product) => record?.variants?.length ?? 0} // Utilise Optional Chaining
      />
      
      {/* TODO: Ajouter EditButton, ShowButton si nécessaire */} 
    </Datagrid>
  </List>
);

/**
 * Composant pour éditer un produit existant.
 */
export const ProductEdit = () => (
    <Edit mutationMode="pessimistic"> 
        <SimpleForm>
            <TextInput source="id" disabled /> 
            <TextInput source="name" label="Nom du Produit" fullWidth required />
            <TextInput source="base_description" label="Description de Base" multiline fullWidth />
            
            {/* Sélection de la catégorie via une liste déroulante */}
            <ReferenceInput source="category_id" reference="categories">
                {/* Récupère la liste des catégories depuis la ressource 'categories' */} 
                <SelectInput optionText="name" label="Catégorie" fullWidth /> 
            </ReferenceInput>

            {/* Affichage des variations (non éditable pour le moment) */} 
            <ArrayField source="variants" label="Variations Existantes"> 
                <SimpleDatagrid bulkActionButtons={false}> 
                    <TextField source="id" label="ID Var." /> 
                    <TextField source="sku" label="SKU" /> 
                    <NumberField source="price" label="Prix" /> 
                </SimpleDatagrid> 
            </ArrayField>
            
        </SimpleForm>
    </Edit>
);

/**
 * Composant pour créer un nouveau produit de base.
 */
export const ProductCreate = () => (
    <Create redirect="list"> 
        <SimpleForm>
            <TextInput source="name" label="Nom du Produit" fullWidth required />
            <TextInput source="base_description" label="Description de Base" multiline fullWidth />
            
            {/* Sélection de la catégorie via une liste déroulante */}
            <ReferenceInput source="category_id" reference="categories">
                 <SelectInput optionText="name" label="Catégorie" fullWidth /> 
            </ReferenceInput>
        </SimpleForm>
    </Create>
);


// Définition de type simple (à affiner ou déplacer dans src/shared/types)
declare module '../types' { // Ajustement potentiel du chemin
    export interface ProductVariant {
        id: number;
        sku: string;
        price?: number;
        attributes?: any;
    }
    export interface Category {
        id: number;
        name: string;
    }
    export interface Product {
        id: number;
        name: string;
        base_description?: string;
        category_id?: number;
        category?: Category;
        variants: ProductVariant[];
    }
} 