# Instalacion paso a paso — maryhug GitHub Profile

## Archivos incluidos

```
maryhug-profile.svg          <- la tarjeta visual
README.md                    <- lo que ve GitHub en tu perfil
.github/
  workflows/
    refresh.yml              <- accion que actualiza los stats automaticamente
```

---

## Pasos

### 1. Abre tu repo de perfil en GitHub
Ve a: https://github.com/maryhug/maryhug

### 2. Sube los 3 archivos
Opciones:

**Opcion A — desde la web (mas facil):**
1. En tu repo haz click en **Add file → Upload files**
2. Arrastra los 3 archivos/carpetas:
   - `maryhug-profile.svg`
   - `README.md`
   - `.github/workflows/refresh.yml`
   > Para la carpeta `.github` tienes que subirla con Git (opcion B)

**Opcion B — con Git (recomendada):**
```bash
# Clona tu repo
git clone https://github.com/maryhug/maryhug.git
cd maryhug

# Copia los archivos aqui adentro
# (reemplaza la ruta con donde descargaste los archivos)
cp ~/Downloads/maryhug-profile.svg .
cp ~/Downloads/README.md .
mkdir -p .github/workflows
cp ~/Downloads/refresh.yml .github/workflows/

# Sube todo
git add .
git commit -m "feat: add animated profile card"
git push
```

### 3. Activa los permisos del Action
1. Ve a tu repo → **Settings → Actions → General**
2. En "Workflow permissions" selecciona **Read and write permissions**
3. Haz click en **Save**

### 4. Ejecuta el Action por primera vez
1. Ve a tu repo → **Actions**
2. Click en **"Refresh profile stats"**
3. Click en **"Run workflow"** → **Run workflow**

### 5. Verifica tu perfil
Ve a https://github.com/maryhug y deberia verse la tarjeta.

> Si no aparece la imagen: espera 1-2 minutos y recarga. GitHub cachea los SVGs.
> Si sigue sin aparecer: abre la URL del SVG directamente y agrega `?v=2` al final para forzar el cache.

---

## Como se actualiza automaticamente

El archivo `refresh.yml` programa una tarea diaria a las 6am UTC que:
1. Toca el SVG para romper el cache de GitHub
2. Hace commit automaticamente

Las imagenes dentro del SVG (GitHub Stats y Commit Streak) se cargan desde APIs externas cada vez que alguien visita tu perfil, asi que siempre muestran datos en tiempo real.

---

## Editar la tarjeta en el futuro

Abre `maryhug-profile.svg` en cualquier editor de texto y modifica:
- **Textos**: busca el contenido entre etiquetas `<text>`
- **Colores**: busca `#d6336c` (rosa principal) y cambialo
- **Stats hardcodeados** (contribuciones, racha): busca los numeros `402`, `1`, `5`
