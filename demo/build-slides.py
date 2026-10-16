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
    obs = json.loads((ROOT / 'docs/CLOUD_OBSERVABILITY_VERIFICATION.json').read_text(encoding='utf-8-sig'))
    gitops = json.loads((ROOT / 'docs/CLOUD_RUNTIME_VERIFICATION.json').read_text(encoding='utf-8-sig'))
    aws = json.loads((ROOT / 'docs/AWS_VERIFICATION.json').read_text(encoding='utf-8-sig'))
    assert {'baseline', 'release', 'rollback', 'recovery', 'storage'} <= {stage['stage'] for stage in gitops['stages']}
    assert obs['aws_deployed'] and aws['cluster']['status'] == 'ACTIVE'
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
    text('Piyush<br/>DevSecOps capstone | 16 October 2026', 60, 330, 800, 23)
    text('Deployed and verified on AWS EKS in Sydney.', 60, 430, 820, 18, color=MUTED)
    pdf.showPage()

    slide('Inventory workflow', 'Source: docs/CLOUD_RUNTIME_VERIFICATION.json | Actual public AWS application')
    bullets(['Product catalog', 'Receipts and issues', 'Append-only movement history', 'Low-stock reporting'], width=260, size=22)
    image('docs/screenshots/stockflow-cloud-overview.png', 340, 128, 565, 350)
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

    slide('AWS infrastructure', 'Source: docs/AWS_VERIFICATION.json and docs/DEPLOYMENT_REVIEW_20261016.json')
    text('Sydney | EKS | private worker | NAT | public ALB | gp3', 62, 135, 830, 28, color=TEAL, bold=True)
    bullets(['EKS ACTIVE; five active managed add-ons.', 'One private m7i-flex.large; encrypted gp3 storage.', 'Scoped Pod Identity roles; no worker redundancy.', 'Full demo estimate: $0.33/hour plus variable usage.'], top=225, size=23)
    pdf.showPage()

    slide('Kubernetes and Helm', 'Source: docs/CLOUD_HELM_VERIFICATION.json and docs/AWS_VERIFICATION.json')
    bullets(['Two Ready frontend and backend replicas each.', 'Encrypted Bound gp3 PVC and ordered migration Job.', 'Helm upgrade and database replacement retained stock.', 'Public ALB frontend and API targets are healthy.'], top=140, size=25)
    pdf.showPage()

    slide('GitOps release and rollback', 'Source: docs/CLOUD_RUNTIME_VERIFICATION.json | Actual EKS ArgoCD')
    text('Green source CI > release-values commit > ArgoCD sync', 62, 135, 830, 27, color=TEAL, bold=True)
    bullets(['Initial sync: Synced and Healthy, with migration hooks.', 'A Git promotion changed both published image SHA tags.', 'Reverting that commit restored the previous image release.', 'Quantity 7 and the same PVC survived both changes.'], top=225, size=22)
    pdf.showPage()

    slide('Live monitoring', 'Source: docs/CLOUD_OBSERVABILITY_VERIFICATION.json | Actual EKS Grafana')
    image('docs/screenshots/stockflow-grafana-cloud.png', 46, 110, 866, 350)
    text(f'{obs["load"]["requests"]:,} read requests; {obs["load"]["failed"]} failures; HPA observed 2 > 3 ready replicas', 60, 466, 840, 17, color=TEAL, bold=True)
    pdf.showPage()

    slide('Recovery and lessons', 'Source: docs/CLOUD_RUNTIME_VERIFICATION.json and docs/CLOUD_VERIFICATION.md')
    bullets(['Backend and database replacement Pods became Ready.', 'Quantity 7 survived release, rollback, and recovery.', 'ArgoCD sync must preserve database migration hooks.', 'Managed project policy required EKS Pod Identity.'], top=140, size=25)
    pdf.showPage()

    slide('Evaluation and cleanup', 'Source: docs/CLOUD_VERIFICATION.md and demo/RECORDING.md')
    bullets(['Silent walkthrough explains the project with captions.', 'Keep the live demo for the agreed evaluation window.', 'AWS continues using credits: about $8/day plus usage.', 'Back up data, remove the ALB/workloads, then destroy Terraform.'], top=135, size=24)
    text('Open live StockFlow | Destroy removes this public URL.', 62, 435, 820, 18, color=TEAL)
    pdf.linkURL(gitops['origin'], (62, 76, 520, 108), relative=0)
    pdf.showPage()
    pdf.save()
    print(f'Created {len(pages)} slides: {OUT}')


if __name__ == '__main__':
    main()
