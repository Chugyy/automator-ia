# Guide Date Calculator

## Configuration requise

### Paramètres obligatoires
Aucun paramètre obligatoire.

### Paramètres optionnels
- **default_format** : Format de date par défaut (défaut: `"%d/%m/%Y"`)
- **timezone** : Fuseau horaire (défaut: `"Europe/Paris"`)
- **locale** : Locale pour les noms (défaut: `"fr_FR"`)

## Action disponible

### calculate_date
Calcule une date relative à aujourd'hui avec descriptions intelligentes.

#### Paramètres
- **days** : Nombre de jours à ajouter/soustraire (défaut: `0`)
- **weeks** : Nombre de semaines à ajouter/soustraire (défaut: `0`)
- **weekday** : Jour de la semaine cible (0=lundi, 6=dimanche)
- **format** : Format de date désiré (optionnel)

#### Priorités
1. **days** et **weeks** ont priorité sur **weekday**
2. Si **weekday** est spécifié seul, trouve le prochain jour de la semaine
3. Les calculs sont cumulatifs : `days + weeks`

## Exemples d'utilisation

### Dates basiques
```json
// Aujourd'hui
{
  "action": "calculate_date",
  "params": {}
}

// Demain
{
  "action": "calculate_date",
  "params": {"days": 1}
}

// Hier
{
  "action": "calculate_date",
  "params": {"days": -1}
}

// Après-demain
{
  "action": "calculate_date",
  "params": {"days": 2}
}
```

### Calculs avec semaines
```json
// Semaine prochaine
{
  "action": "calculate_date",
  "params": {"weeks": 1}
}

// Semaine dernière
{
  "action": "calculate_date",
  "params": {"weeks": -1}
}

// Dans 2 semaines et 3 jours
{
  "action": "calculate_date",
  "params": {"days": 3, "weeks": 2}
}
```

### Jours de la semaine
```json
// Prochain lundi (weekday: 0)
{
  "action": "calculate_date",
  "params": {"weekday": 0}
}

// Prochain vendredi (weekday: 4)
{
  "action": "calculate_date",
  "params": {"weekday": 4}
}

// Prochain dimanche (weekday: 6)
{
  "action": "calculate_date",
  "params": {"weekday": 6}
}
```

### Formats personnalisés
```json
// Format ISO
{
  "action": "calculate_date",
  "params": {
    "days": 7,
    "format": "%Y-%m-%d"
  }
}

// Format complet
{
  "action": "calculate_date",
  "params": {
    "days": 1,
    "format": "%A %d %B %Y"
  }
}

// Format abrégé
{
  "action": "calculate_date",
  "params": {
    "weeks": 1,
    "format": "%d %b %Y"
  }
}
```

## Correspondance jours de la semaine
- **0** = Lundi
- **1** = Mardi
- **2** = Mercredi
- **3** = Jeudi
- **4** = Vendredi
- **5** = Samedi
- **6** = Dimanche

## Formats de date disponibles

### Formats courants
| Format | Exemple | Description |
|--------|---------|-------------|
| `%d/%m/%Y` | 31/12/2024 | Jour/mois/année (français) |
| `%m/%d/%Y` | 12/31/2024 | Mois/jour/année (US) |
| `%Y-%m-%d` | 2024-12-31 | Format ISO |
| `%d %b %Y` | 31 Déc 2024 | Jour mois abrégé année |
| `%A %d %B %Y` | Mardi 31 Décembre 2024 | Format complet |

### Codes de format
- `%d` - Jour du mois (01-31)
- `%m` - Mois numérique (01-12)
- `%Y` - Année complète (2024)
- `%y` - Année sur 2 chiffres (24)
- `%b` - Mois abrégé (Déc)
- `%B` - Mois complet (Décembre)
- `%a` - Jour abrégé (Mar)
- `%A` - Jour complet (Mardi)

## Exemples de configuration

### Configuration par défaut (France)
```json
{
  "default_format": "%d/%m/%Y",
  "timezone": "Europe/Paris",
  "locale": "fr_FR"
}
```

### Configuration US
```json
{
  "default_format": "%m/%d/%Y",
  "timezone": "America/New_York",
  "locale": "en_US"
}
```

### Configuration ISO
```json
{
  "default_format": "%Y-%m-%d",
  "timezone": "UTC",
  "locale": "en_US"
}
```

## Cas spéciaux

### Raccourcis pratiques
- **Hier** : `{"days": -1}`
- **Demain** : `{"days": 1}`
- **Après-demain** : `{"days": 2}`
- **Semaine prochaine** : `{"weeks": 1}`
- **Semaine dernière** : `{"weeks": -1}`

### Calculs complexes
```json
// Dans 1 mois et 2 jours (approximatif)
{
  "action": "calculate_date",
  "params": {"days": 32}
}

// Il y a 3 semaines et 4 jours
{
  "action": "calculate_date",
  "params": {"days": -4, "weeks": -3}
}
```

## Timezones supportées
- `Europe/Paris`
- `America/New_York`
- `America/Los_Angeles`
- `Asia/Tokyo`
- `UTC`
- etc. (toute timezone IANA)