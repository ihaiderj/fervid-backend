from django.http import HttpResponse
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView

from brochures.models import Brochure
from brochures.storage import delete_by_url, open_by_url, save_uploaded_file
from core.mixins import APIResponseMixin
from core.permissions import IsAdminOrMR


class BrochureUploadView(APIResponseMixin, APIView):
    permission_classes = [IsAdminOrMR]
    parser_classes = [MultiPartParser]

    def post(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return self.error("No file provided", code="NO_FILE")

        file_url = save_uploaded_file(uploaded, "brochures")
        return self.success(
            {
                "file_url": file_url,
                "file_name": uploaded.name,
                "file_type": uploaded.content_type,
                "file_size": str(uploaded.size),
            },
            status_code=201,
        )


class BrochureDownloadView(APIResponseMixin, APIView):
    permission_classes = [IsAdminOrMR]

    def get(self, request, pk):
        try:
            brochure = Brochure.objects.get(id=pk, is_deleted=False)
        except Brochure.DoesNotExist:
            return self.error("Brochure not found", code="NOT_FOUND", status_code=404)

        brochure.view_count += 1
        brochure.save(update_fields=["view_count", "updated_at"])

        if brochure.file_url:
            try:
                with open_by_url(brochure.file_url) as f:
                    data = f.read()
                brochure.download_count += 1
                brochure.save(update_fields=["download_count"])
                filename = brochure.file_name or "brochure"
                response = HttpResponse(
                    data, content_type=brochure.file_type or "application/octet-stream"
                )
                response["Content-Disposition"] = f'attachment; filename="{filename}"'
                return response
            except FileNotFoundError:
                pass

        return self.success({"file_url": brochure.file_url})


class BrochureFileDeleteView(APIResponseMixin, APIView):
    permission_classes = [IsAdminOrMR]

    def delete(self, request, pk):
        try:
            brochure = Brochure.objects.get(id=pk)
        except Brochure.DoesNotExist:
            return self.error("Not found", code="NOT_FOUND", status_code=404)

        if brochure.file_url:
            delete_by_url(brochure.file_url)

        brochure.file_url = ""
        brochure.save(update_fields=["file_url"])
        return self.success(message="File deleted")


class DoctorPhotoUploadView(APIResponseMixin, APIView):
    permission_classes = [IsAdminOrMR]
    parser_classes = [MultiPartParser]

    def post(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return self.error("No file provided", code="NO_FILE")

        file_url = save_uploaded_file(uploaded, "doctor_photos")

        doctor_id = request.data.get("doctor_id")
        if doctor_id:
            from doctors.models import Doctor, DoctorAssignment

            doctor = Doctor.objects.filter(id=doctor_id, is_deleted=False).first()
            if not doctor:
                return self.error("Doctor not found", code="NOT_FOUND", status_code=404)

            if request.user.role != "admin":
                if not DoctorAssignment.objects.filter(
                    doctor=doctor, mr=request.user, status="active"
                ).exists():
                    return self.error("Not assigned to this doctor", code="FORBIDDEN", status_code=403)

            doctor.profile_image_url = file_url
            doctor.save(update_fields=["profile_image_url", "updated_at"])

        return self.success({"file_url": file_url}, status_code=201)
