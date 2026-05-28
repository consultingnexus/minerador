from .base import CollectorResult
from .cnpj import collect_cnpj
from .site import collect_site
from .pagespeed import collect_pagespeed
from .noticias import collect_noticias

# Experimentais — frágeis, fora do default
from .google_maps import collect_google_maps
from .reclame_aqui import collect_reclame_aqui
from .linkedin import collect_linkedin
from .vagas import collect_vagas

COLLECTORS = {
    # estáveis
    "cnpj": collect_cnpj,
    "site": collect_site,
    "pagespeed": collect_pagespeed,
    "noticias": collect_noticias,
    # experimentais (não executam por padrão)
    "google_maps": collect_google_maps,
    "reclame_aqui": collect_reclame_aqui,
    "linkedin": collect_linkedin,
    "vagas": collect_vagas,
}
