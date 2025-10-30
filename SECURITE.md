# Note de sécurité

## Comptes configurés

L'application contient deux comptes préconfigurés :

1. **fournigoogle** / fournigoogle1! (rôle : google)
2. **fourniavis** / fourniavis1! (rôle : avis)

## ⚠️ Avertissement de sécurité

**Important :** Stocker des identifiants dans un dépôt GitHub public présente des risques de sécurité. Les mots de passe (même hachés) et la base de données sont accessibles à tous.

### Recommandations :
- Utilisez un dépôt GitHub **privé** pour ce projet
- Changez les mots de passe régulièrement
- Considérez l'utilisation de variables d'environnement pour les secrets sensibles

## Réinitialisation des comptes

Si vous devez réinitialiser les comptes, exécutez :

```bash
cd gestion-fiches-main
python init_comptes.py
```

Cela supprimera tous les comptes existants et créera uniquement les deux comptes ci-dessus.
