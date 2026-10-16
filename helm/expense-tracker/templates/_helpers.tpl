{{/* Chart name */}}
{{- define "expense-tracker.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Fully qualified name. When the release is named like the chart (helm install expense-tracker ...)
I collapse "expense-tracker-expense-tracker" to "expense-tracker" so Service names stay readable
and match the BACKEND_HOST default baked into the frontend image.
*/}}
{{- define "expense-tracker.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := include "expense-tracker.name" . -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/* Common labels (recommended app.kubernetes.io/* set) */}}
{{- define "expense-tracker.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "expense-tracker.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: expense-tracker
{{- end -}}

{{/*
Selector labels for one component. Usage:
  include "expense-tracker.selectorLabels" (dict "root" . "component" "backend")
The plain `app` label is what the standalone monitoring/ and troubleshooting/ manifests select on.
*/}}
{{- define "expense-tracker.selectorLabels" -}}
app: {{ include "expense-tracker.fullname" .root }}-{{ .component }}
app.kubernetes.io/name: {{ include "expense-tracker.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/* Image references; the tag falls back to appVersion so a plain `helm install` deploys a known release */}}
{{- define "expense-tracker.backendImage" -}}
{{ .Values.backend.image.repository }}:{{ .Values.backend.image.tag | default .Chart.AppVersion }}
{{- end -}}
{{- define "expense-tracker.frontendImage" -}}
{{ .Values.frontend.image.repository }}:{{ .Values.frontend.image.tag | default .Chart.AppVersion }}
{{- end -}}

{{/* Name of the Secret that holds POSTGRES_USER / POSTGRES_PASSWORD / DATABASE_URL */}}
{{- define "expense-tracker.secretName" -}}
{{- if .Values.postgres.existingSecret -}}
{{ .Values.postgres.existingSecret }}
{{- else -}}
{{ include "expense-tracker.fullname" . }}-secrets
{{- end -}}
{{- end -}}

{{/* SQLAlchemy URL rendered into the chart-managed Secret (psycopg 3 driver) */}}
{{- define "expense-tracker.databaseUrl" -}}
{{- if .Values.postgres.enabled -}}
postgresql+psycopg://{{ .Values.postgres.username }}:{{ .Values.postgres.password }}@{{ include "expense-tracker.fullname" . }}-postgres:5432/{{ .Values.postgres.database }}
{{- else -}}
{{ required "externalDatabaseUrl is required when postgres.enabled=false and no existingSecret is set" .Values.externalDatabaseUrl }}
{{- end -}}
{{- end -}}
