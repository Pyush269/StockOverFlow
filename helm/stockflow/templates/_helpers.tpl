{{- define "stockflow.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 40 | trimSuffix "-" -}}
{{- end -}}
{{- define "stockflow.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: stockflow
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | quote }}
{{- end -}}
{{- define "stockflow.selector" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
{{- define "stockflow.podSecurity" -}}
runAsNonRoot: true
seccompProfile:
  type: RuntimeDefault
{{- end -}}
{{- define "stockflow.containerSecurity" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: [ALL]
{{- end -}}
{{- define "stockflow.pullSecrets" -}}
{{- with .Values.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end -}}
{{- define "stockflow.backendImage" -}}
{{- printf "%s:%s" .Values.backend.image.repository .Values.backend.image.tag -}}
{{- end -}}
{{- define "stockflow.frontendImage" -}}
{{- printf "%s:%s" .Values.frontend.image.repository .Values.frontend.image.tag -}}
{{- end -}}
{{- define "stockflow.databaseEnv" -}}
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ .Values.postgresql.existingSecret }}
      key: database-url
{{- end -}}
