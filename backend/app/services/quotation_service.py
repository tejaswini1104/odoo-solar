from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.models import Quotation, QuotationItem, SiteSurvey, SolarPackage, Customer
from backend.app.schemas.schemas import QuotationCreate

class QuotationService:
    @staticmethod
    def create_quotation(db: Session, quotation_in: QuotationCreate) -> Quotation:
        # 1. HARD GATE: Survey check
        survey = db.query(SiteSurvey).filter(SiteSurvey.id == quotation_in.survey_id).first()
        if not survey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site survey with ID {quotation_in.survey_id} not found."
            )
        
        # Hard check enforced in backend service layer
        if survey.status != "Approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Quotation cannot be created: linked site survey is not Approved. Current status is '{survey.status}'. A survey approval is mandatory."
            )

        # 2. Customer check
        customer = db.query(Customer).filter(Customer.id == quotation_in.customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {quotation_in.customer_id} not found."
            )

        # 3. Package check & auto BOM generation
        package = db.query(SolarPackage).filter(SolarPackage.id == quotation_in.package_id).first()
        if not package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Solar package with ID {quotation_in.package_id} not found."
            )

        # 4. The package must match what the survey recommended, unless Sales give a reason for choosing another
        override_reason = (quotation_in.override_reason or "").strip() or None
        mismatches = []
        if survey.recommended_capacity is not None and abs(package.capacity_kw - survey.recommended_capacity) > 0.01:
            mismatches.append(f"{survey.recommended_capacity:g} kW")
        if survey.recommended_system_type and package.system_type != survey.recommended_system_type:
            mismatches.append(survey.recommended_system_type)
        if mismatches and not override_reason:
            wanted = " ".join(
                part for part in (
                    f"{survey.recommended_capacity:g} kW" if survey.recommended_capacity is not None else None,
                    survey.recommended_system_type,
                ) if part
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"The survey recommends {wanted}, but this package is {package.capacity_kw:g} kW "
                    f"{package.system_type}. Choose the recommended package, or give a reason for the change."
                ),
            )

        # Create quotation record
        quotation = Quotation(
            customer_id=customer.id,
            survey_id=survey.id,
            package_id=package.id,
            override_reason=override_reason if mismatches else None,
            status="Draft",
            subtotal=0.0,
            tax=0.0,
            total=0.0
        )
        db.add(quotation)
        db.flush() # get quotation.id

        # Auto BOM from package components
        subtotal = 0.0
        for comp in package.components:
            product = comp.product
            item_total = comp.quantity * product.unit_price
            subtotal += item_total
            
            q_item = QuotationItem(
                quotation_id=quotation.id,
                product_id=product.id,
                quantity=comp.quantity,
                unit_price=product.unit_price,
                total_price=item_total
            )
            db.add(q_item)

        # 18% GST standard on solar installations
        tax = round(subtotal * 0.18, 2)
        total = round(subtotal + tax, 2)

        quotation.subtotal = subtotal
        quotation.tax = tax
        quotation.total = total

        db.commit()
        db.refresh(quotation)
        return quotation
