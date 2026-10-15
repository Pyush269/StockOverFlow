"""Generate the submission's PDF slides from recorded project evidence."""
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'demo/slides.pdf'
W, H = 960, 540
INK = colors.HexColor('#143C3A')
TEAL = colors.HexColor('#087F74')
MUTED = colors.HexColor('#536A68')
PAPER = colors.HexColor('#F6F5EF')
REPO = 'https://github.com/Pyush269/StockOverFlow'


def main():
    obs = json.loads((ROOT / 'docs/OBSERVABILITY_VERIFICATION.json').read_text(encoding='utf-8-sig'))
    gitops = json.loads((ROOT / 'docs/GITOPS_VERIFICATION.json').read_text(encoding='utf-8-sig'))
    assert {'baseline', 'release', 'rollback', 'recovery'} <= {stage['stage'] for stage in gitops['stages']}
    assert obs['hpa_scaled_above_two'] and obs['load']['failed'] == 0
    pdf = canvas.Canvas(str(OUT), pagesize=(W, H))
    pdf.setTitle('StockFlow - DevSecOps capstone')
    pdf.setAuthor('Piyush')
    pages = []

    def text(value, x, top, width, size=22, color=INK, bold=False):
        style = ParagraphStyle('slide', fontName='Helvetica-Bold' if bold else 'Helvetica', fontSize=size, leading=size * 1.35, textColor=color)
        paragraph = Paragraph(value, style)
        _, height = paragraph.wrap(width, 450)
        if top + height > 490:
            raise ValueError('Slide text overflows: ' + value[:50])
        paragraph.drawOn(pdf, x, H - top - height)
        return top + height

    def slide(title, source):
        pdf.setFillColor(PAPER)
        pdf.rect(0, 0, W, H, fill=1, stroke=0)
        text(title, 52, 42, 856, 34, bold=True)
        pdf.setFillColor(MUTED)
        pdf.setFont('Helvetica', 9)
        pdf.drawString(52, 22, source)
        pdf.drawRightString(908, 22, f'{len(pages) + 1} / 11')
        pages.append(title)

    def bullets(items, x=62, top=135, width=820, size=23):
        for item in items:
            top = text(item, x, top, width, size) + 21
        return top

    def image(relative, x, top, width, height):
        reader = ImageReader(str(ROOT / relative))
        iw, ih = reader.getSize()
        factor = min(width / iw, height / ih)
        dw, dh = iw * factor, ih * factor
        pdf.drawImage(reader, x + (width - dw) / 2, H - top - dh, dw, dh, preserveAspectRatio=True, mask='auto')

    slide('StockFlow', REPO)
    text('Inventory management with a stock movement ledger', 56, 160, 800, 38, color=TEAL)
    text('Piyush<br/>DevSecOps capstone | 15 October 2026', 60, 330, 800, 23)
    text('Local implementation verified. AWS deployment remains pending.', 60, 430, 820, 18, color=MUTED)
    pdf.showPage()

    slide('Inventory workflow', 'Source: StockFlow application and docs/CONTAINERS.md | Actual local screenshot')
    bullets(['Product catalog', 'Receipts and issues', 'Append-only movement history', 'Low-stock reporting'], width=260, size=22)
    image('docs/screenshots/container-overview-qa.png', 340, 128, 565, 350)
    pdf.showPage()

    slide('Application architecture', 'Source: backend/app/, backend/alembic/, docker-compose.yml')
    # Technical component diagram; text and connectors remain vector PDF objects.
    for label, x, width in [('React / Nginx', 62, 240), ('FastAPI', 395, 160), ('PostgreSQL 16', 690, 215)]:
        text(label, x, 145, width, 27, color=TEAL, bold=True)
    pdf.setStrokeColor(TEAL)
    pdf.setLineWidth(1.5)
    for start, end in [(280, 365), (545, 655)]:
        pdf.line(start, 374, end, 374)
        pdf.line(end - 8, 379, end, 374)
        pdf.line(end - 8, 369, end, 374)
    bullets(['Browser calls use relative /api paths.', 'Alembic applies the schema before API readiness.', 'Row locks serialize competing stock changes.', 'Inventory and ledger writes share one transaction.'], top=225, size=22)
    pdf.showPage()

    slide('Tests and local containers', 'Source: docs/CI_RELEASE.json, docs/FRONTEND_VERIFICATION.md, docs/CONTAINERS.md')
    text('49 backend tests | 11 frontend unit tests | 8 browser workflows', 62, 135, 830, 27, color=TEAL, bold=True)
    bullets(['Real PostgreSQL tests cover concurrency and rollback.', 'Disposable test databases protect development inventory.', 'Compose starts the database, migration, API, and UI.', 'Both application images run as non-root users.'], top=235, size=22)
    pdf.showPage()

    slide('CI and image security', 'Source: .github/workflows/ci.yml and docs/CI_SECURITY.md')
    text('Tests > image build > Trivy gate > SHA-tagged GHCR images', 62, 140, 830, 27, color=TEAL, bold=True)
    bullets(['HIGH/CRITICAL image findings fail publication.', 'The pipeline publishes the same scanned image bytes.', 'Pull requests receive no package publication credentials.', 'Terraform has three separate documented scan findings.'], top=235, size=22)
    pdf.showPage()

    slide('AWS infrastructure - deployment pending', 'Source: docs/INFRASTRUCTURE_REVIEW.json | USD estimate, before variable usage and credits')
    text('Sydney | EKS | private worker | NAT | public ALB | gp3', 62, 135, 830, 28, color=TEAL, bold=True)
    bullets(['Reviewed plan: 59 additions; one m7i-flex.large worker.', 'Infrastructure estimate: $0.29/hour.', 'Illustrative full demo estimate: $0.33/hour.', 'A single worker has no worker redundancy.'], top=225, size=23)
    pdf.showPage()

    slide('Kubernetes and Helm', 'Source: docs/HELM.md and docs/HELM_VERIFICATION.json | Local verification')
    bullets(['Two frontend and backend replicas with health probes.', 'Persistent PostgreSQL PVC and ordered migration Job.', 'Helm upgrade and database pod replacement retained stock.', 'Cloud EBS/IRSA and ALB routing still need verification.'], top=140, size=25)
    pdf.showPage()

    slide('GitOps release and rollback', 'Source: docs/GITOPS_VERIFICATION.json and argocd/README.md | Local ArgoCD')
    text('Green source CI > release-values commit > ArgoCD sync', 62, 135, 830, 27, color=TEAL, bold=True)
    bullets(['Initial sync: Synced and Healthy, with migration hooks.', 'A Git promotion changed both published image SHA tags.', 'Reverting that commit restored the previous image release.', 'Quantity 7 and the same PVC survived both changes.'], top=225, size=22)
    pdf.showPage()

    slide('Live monitoring', 'Source: docs/OBSERVABILITY_VERIFICATION.json | Actual local Grafana screenshot')
    image('docs/screenshots/stockflow-grafana-local.png', 46, 110, 866, 350)
    text(f'{obs["load"]["requests"]:,} read requests; {obs["load"]["failed"]} failures; HPA observed 2 > 3 ready replicas', 60, 466, 840, 17, color=TEAL, bold=True)
    pdf.showPage()

    slide('Recovery and lessons', 'Source: docs/GITOPS_VERIFICATION.json and docs/OBSERVABILITY_VERIFICATION.json')
    bullets(['A replacement backend Pod restored healthy replicas.', 'Persistent inventory survived release and rollback.', 'ArgoCD sync must preserve database migration hooks.', 'Longer monitoring exposed Grafana sidecar memory limits.'], top=140, size=25)
    pdf.showPage()

    slide('Evaluation and cleanup', 'Source: docs/INFRASTRUCTURE.md and demo/RECORDING.md | Cloud evidence remains pending')
    bullets(['Next: deploy and verify EKS, EBS, public ALB, and cloud GitOps.', 'Record the mandatory walkthrough with actual cloud evidence.', 'Keep the live demo until evaluation, unless instructed otherwise.', 'Back up data, remove the ALB/workloads, then destroy Terraform.'], top=135, size=24)
    text('Destroy stops the public URL. Source code and saved evidence remain.', 62, 435, 820, 18, color=MUTED)
    pdf.showPage()
    pdf.save()
    print(f'Created {len(pages)} slides: {OUT}')


if __name__ == '__main__':
    main()
