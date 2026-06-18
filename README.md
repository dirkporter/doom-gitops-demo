# DOOM GitOps Demo (OpenShift 4.21 + GitOps + RHACM + Virtualization)

A multi-product demo: a DOOM web container posts level-completion times to a
Python API, which stores them in PostgreSQL running inside a VM (OpenShift
Virtualization). RHACM Placement decides which clusters get the app, and
OpenShift GitOps (Argo CD) deploys it there via an ApplicationSet.

Assumes you already have the **OpenShift GitOps**, **OpenShift Virtualization**,
and **RHACM** operators installed and healthy on the hub.

## Repo layout

```
doom-gitops-demo/
├── rhacm/
│   ├── managedclustersetbinding.yaml
│   ├── placement.yaml
│   ├── gitops-cluster.yaml
│   └── acm-placement-configmap.yaml      # NEW - required by the ApplicationSet generator
├── bootstrap/
│   └── doom-applicationset.yaml          # REPLACES the old root-app.yaml
├── manifests/                            # what Argo CD syncs to each selected cluster
│   ├── namespace.yaml
│   ├── db-virtualmachine.yaml
│   ├── api-deployment.yaml
│   └── doom-deployment.yaml
├── build/                                # optional build-once API image
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
└── test/
    └── smoke-test.sh
```

## What changed from the original blueprint (and why)

1. **VM had no network.** The VM defined no `interfaces`/`networks`, so it
   booted with no NIC: cloud-init couldn't reach dnf repos and the DB was
   unreachable. Added a masquerade pod-network interface. Also switched the
   deprecated `spec.running: true` to `spec.runStrategy: Always`, and added
   GRANTs so the app user (`doom_admin`) can use the table that the `postgres`
   user creates.
2. **Placement was ignored.** The old root `Application` deployed to
   `kubernetes.default.svc` (the hub) regardless of the Placement. Replaced it
   with an **ApplicationSet** using the `clusterDecisionResource` generator, plus
   the `acm-placement` ConfigMap it depends on. Now the app lands on exactly the
   clusters you label `demo=doom`.
3. **API crash-looped on OpenShift.** It wrote `app.py` to `/` and pip-installed
   into system site-packages - both forbidden for the random UID under the
   `restricted-v2` SCC. Code now arrives read-only via a ConfigMap at
   `/opt/app`; deps install into `/tmp`. Added `/healthz` (startup probe) and
   `/scores`.
4. **Route port mismatch.** The Route referenced `targetPort: 8080`, but a Route
   must point at the *service* port (80). Service ports are now named `http` and
   the Route references the name.
5. **Invalid syncPolicy field** (`createNamespace: true`) replaced with the
   correct `syncOptions: [CreateNamespace=true]`.

## Heads-up: RHACM channel vs OpenShift 4.21

The original Subscription pinned `release-2.13`, which predates 4.21 and won't
list it as supported. RHACM supports the current OCP release plus the two prior
and the next; for **4.21** use **RHACM 2.16** (released with MCE 2.11) - confirm
against the 2.16 support matrix for your exact 4.21.z. You said RHACM is already
installed, so this is just an FYI if you ever reinstall.

## Heads-up: the DOOM image

`ghcr.io/greg-jones/web-doom:latest` is a **placeholder**. For times to be
recorded, the image must read `DOOM_API_URL` and POST
`{"player_id","level","time_seconds"}` as JSON on level completion. Stock
browser-DOOM images don't do this - you'll need a build with that hook. Until
then, prove the data path with `test/smoke-test.sh`.

## Deploy order

1. Push this repo to GitHub and set your repo URL in
   `bootstrap/doom-applicationset.yaml`.
2. On the **hub**, apply the RHACM wiring:
   ```bash
   oc apply -f rhacm/managedclustersetbinding.yaml
   oc apply -f rhacm/acm-placement-configmap.yaml
   oc apply -f rhacm/placement.yaml
   oc apply -f rhacm/gitops-cluster.yaml
   ```
3. Label the clusters that should run the demo (RHACM console → Infrastructure →
   Clusters → Edit labels, or):
   ```bash
   oc label managedcluster local-cluster demo=doom --overwrite
   ```
4. Apply the ApplicationSet:
   ```bash
   oc apply -f bootstrap/doom-applicationset.yaml
   ```
   Argo CD creates one `doom-demo-<cluster>` Application per labeled cluster and
   syncs `manifests/` there.

## Verify

```bash
oc -n doom-demo get vm,pods,svc,route
bash test/smoke-test.sh
```

The VM takes a couple of minutes on first boot (cloud-init installs PostgreSQL).

## Caveats

- The DB boots from an ephemeral `containerDisk`; rows are lost on VM restart.
  For persistence, replace the containerDisk volume with a DataVolume/PVC backed
  by a CDI source and your storage class.
- The inline API installs from PyPI at startup (needs egress). For a sealed
  image, build `build/` and swap the container per the Dockerfile comments.
- Demo passwords are hardcoded - fine for a lab, not for anything real.
