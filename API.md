# API Documentation



❌130 ❯ curl -v -X POST http://localhost:8000/checklist/start | jq
* Host localhost:8000 was resolved.
* IPv6: ::1
* IPv4: 127.0.0.1
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0*   Trying [::1]:8000...
* Connected to localhost (::1) port 8000
> POST /checklist/start HTTP/1.1
> Host: localhost:8000
> User-Agent: curl/8.7.1
> Accept: */*
>
* Request completely sent off
< HTTP/1.1 200 OK
< date: Sun, 16 Nov 2025 02:10:15 GMT
< server: uvicorn
< content-length: 692
< content-type: application/json
<
{ [692 bytes data]
100   692  100   692    0     0   130k      0 --:--:-- --:--:-- --:--:--  135k
* Connection #0 to host localhost left intact
{
  "checklist_id": "a251c633-1bcb-498d-80c3-bc50d3d09f78",
  "steps": [
    {
      "step_id": "step_1",
      "name": "Fuel Quantity",
      "description": "Confirm fuel quantity is adequate for flight."
    },
    {
      "step_id": "step_2",
      "name": "Oil Pressure",
      "description": "Check engine oil pressure is within normal range."
    },
    {
      "step_id": "step_3",
      "name": "Oil Temperature",
      "description": "Verify oil temperature is within limits."
    },
    {
      "step_id": "step_4",
      "name": "Engine RPM",
      "description": "Ensure engine RPM is within normal operating range."
    },
    {
      "step_id": "step_5",
      "name": "Manifold Pressure",
      "description": "Check manifold pressure is within normal range."
    }
  ],
  "message": "Checklist started. Use /checklist/next/<step_id> to proceed with each step."
}

~/c/p/aviation-hackathon-sf on  main [?⇡] via 🐳 desktop-linux is 📦 v0.0.1 via 🐍 v3.13.6 on ☁️  shubhamchaudhary92@gmail.com(us-central1)
❯ curl -v "http://localhost:8000/checklist/status/step_1?checklist_id=3227fb62-c15d-4e92-a33e-fba57cc3dc40" | jq

~/c/p/aviation-hackathon-sf on  main [?⇡] via 🐳 desktop-linux is 📦 v0.0.1 via 🐍 v3.13.6 on ☁️  shubhamchaudhary92@gmail.com(us-central1)
❌130 ❯ curl -v http://localhost:8000/checklist/next/step_1 | jq

~/c/p/aviation-hackathon-sf on  main [?⇡] via 🐳 desktop-linux is 📦 v0.0.1 via 🐍 v3.13.6 on ☁️  shubhamchaudhary92@gmail.com(us-central1)
❌130 ❯ curl -v http://localhost:8000/checklist/next/step_1 | jq
* Host localhost:8000 was resolved.
* IPv6: ::1
* IPv4: 127.0.0.1
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0*   Trying [::1]:8000...
* Connected to localhost (::1) port 8000
> GET /checklist/next/step_1 HTTP/1.1
> Host: localhost:8000
> User-Agent: curl/8.7.1
> Accept: */*
>
* Request completely sent off
< HTTP/1.1 200 OK
< date: Sun, 16 Nov 2025 02:10:37 GMT
< server: uvicorn
< content-length: 150
< content-type: application/json
<
{ [150 bytes data]
100   150  100   150    0     0  23187      0 --:--:-- --:--:-- --:--:-- 25000
* Connection #0 to host localhost left intact
{
  "step_id": "step_1",
  "step_name": "Fuel Quantity",
  "message": "Processing Fuel Quantity. Use /checklist/status/step_1?checklist_id=None to check status."
}

~/c/p/aviation-hackathon-sf on  main [?⇡] via 🐳 desktop-linux is 📦 v0.0.1 via 🐍 v3.13.6 on ☁️  shubhamchaudhary92@gmail.com(us-central1)
❯ curl -v "http://localhost:8000/checklist/next/step_1?checklist_id=68ecf8ee-cd50-4e05-9714-0360f0fe0b2d" | jq
* Host localhost:8000 was resolved.
* IPv6: ::1
* IPv4: 127.0.0.1
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0*   Trying [::1]:8000...
* Connected to localhost (::1) port 8000
> GET /checklist/next/step_1?checklist_id=68ecf8ee-cd50-4e05-9714-0360f0fe0b2d HTTP/1.1
> Host: localhost:8000
> User-Agent: curl/8.7.1
> Accept: */*
>
* Request completely sent off
< HTTP/1.1 200 OK
< date: Sun, 16 Nov 2025 02:10:53 GMT
< server: uvicorn
< content-length: 182
< content-type: application/json
<
{ [182 bytes data]
100   182  100   182    0     0  37203      0 --:--:-- --:--:-- --:--:-- 45500
* Connection #0 to host localhost left intact
{
  "step_id": "step_1",
  "step_name": "Fuel Quantity",
  "message": "Processing Fuel Quantity. Use /checklist/status/step_1?checklist_id=68ecf8ee-cd50-4e05-9714-0360f0fe0b2d to check status."
}

~/c/p/aviation-hackathon-sf on  main [?⇡] via 🐳 desktop-linux is 📦 v0.0.1 via 🐍 v3.13.6 on ☁️  shubhamchaudhary92@gmail.com(us-central1)
❯ curl -v "http://localhost:8000/checklist/status/step_1?checklist_id=3227fb62-c15d-4e92-a33e-fba57cc3dc40" | jq
* Host localhost:8000 was resolved.
* IPv6: ::1
* IPv4: 127.0.0.1
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0*   Trying [::1]:8000...
* Connected to localhost (::1) port 8000
> GET /checklist/status/step_1?checklist_id=3227fb62-c15d-4e92-a33e-fba57cc3dc40 HTTP/1.1
> Host: localhost:8000
> User-Agent: curl/8.7.1
> Accept: */*
>
* Request completely sent off
< HTTP/1.1 200 OK
< date: Sun, 16 Nov 2025 02:10:59 GMT
< server: uvicorn
< content-length: 142
< content-type: application/json
<
{ [142 bytes data]
100   142  100   142    0     0  24929      0 --:--:-- --:--:-- --:--:-- 28400
* Connection #0 to host localhost left intact
{
  "step_id": "step_1",
  "status": "no_data",
  "next_step_id": "step_2",
  "error": null,
  "message": "No telemetry data available for columns: FQtyL, FQtyR"
}

~/c/p/aviation-hackathon-sf on  main [?⇡] via 🐳 desktop-linux is 📦 v0.0.1 via 🐍 v3.13.6 on ☁️  shubhamchaudhary92@gmail.com(us-central1)
❯ curl -v "http://localhost:8000/checklist/status/step_2?checklist_id=3227fb62-c15d-4e92-a33e-fba57cc3dc40" | jq
* Host localhost:8000 was resolved.
* IPv6: ::1
* IPv4: 127.0.0.1
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0*   Trying [::1]:8000...
* Connected to localhost (::1) port 8000
> GET /checklist/status/step_2?checklist_id=3227fb62-c15d-4e92-a33e-fba57cc3dc40 HTTP/1.1
> Host: localhost:8000
> User-Agent: curl/8.7.1
> Accept: */*
>
* Request completely sent off
< HTTP/1.1 200 OK
< date: Sun, 16 Nov 2025 02:11:12 GMT
< server: uvicorn
< content-length: 137
< content-type: application/json
<
{ [137 bytes data]
100   137  100   137    0     0  25239      0 --:--:-- --:--:-- --:--:-- 27400
* Connection #0 to host localhost left intact
{
  "step_id": "step_2",
  "status": "no_data",
  "next_step_id": "step_3",
  "error": null,
  "message": "No telemetry data available for columns: E1 OilP"
}

~/c/p/aviation-hackathon-sf on  main [?⇡] via 🐳 desktop-linux is 📦 v0.0.1 via 🐍 v3.13.6 on ☁️  shubhamchaudhary92@gmail.com(us-central1)
❯ curl -v "http://localhost:8000/checklist/status/step_3?checklist_id=3227fb62-c15d-4e92-a33e-fba57cc3dc40" | jq
* Host localhost:8000 was resolved.
* IPv6: ::1
* IPv4: 127.0.0.1
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0*   Trying [::1]:8000...
* Connected to localhost (::1) port 8000
> GET /checklist/status/step_3?checklist_id=3227fb62-c15d-4e92-a33e-fba57cc3dc40 HTTP/1.1
> Host: localhost:8000
> User-Agent: curl/8.7.1
> Accept: */*
>
* Request completely sent off
< HTTP/1.1 200 OK
< date: Sun, 16 Nov 2025 02:11:21 GMT
< server: uvicorn
< content-length: 137
< content-type: application/json
<
{ [137 bytes data]
100   137  100   137    0     0  24464      0 --:--:-- --:--:-- --:--:-- 27400
* Connection #0 to host localhost left intact
{
  "step_id": "step_3",
  "status": "no_data",
  "next_step_id": "step_4",
  "error": null,
  "message": "No telemetry data available for columns: E1 OilT"
}

~/c/p/aviation-hackathon-sf on  main [?⇡] via 🐳 desktop-linux is 📦 v0.0.1 via 🐍 v3.13.6 on ☁️  shubhamchaudhary92@gmail.com(us-central1)
❯
